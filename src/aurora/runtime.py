import asyncio
from collections import defaultdict
from uuid import uuid4

from google.adk.agents.run_config import RunConfig
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types

from .agents import build_app
from .config import Settings
from .models import configured_model
from .store import Store


class Runtime:
    def __init__(self, settings: Settings, model=None):
        self.store = Store(settings)
        self.sessions = DatabaseSessionService(
            db_url=f"sqlite+aiosqlite:///{settings.adk_db}"
        )
        self.model = model
        self.runner = None
        self.settings = settings
        self.locks = defaultdict(asyncio.Lock)

    def get_runner(self) -> Runner:
        if self.runner is None:
            model = self.model
            if model is None:
                model = configured_model()
            self.runner = Runner(
                app=build_app(self.store, self.settings, model),
                session_service=self.sessions,
            )
        return self.runner

    async def create_session(self, apartment: str) -> str:
        session_id = str(uuid4())
        await self.sessions.create_session(
            app_name="aurora", user_id=session_id, session_id=session_id
        )
        self.store.add_session(session_id, apartment)
        return session_id

    async def get_session(self, session_id: str):
        return await self.sessions.get_session(
            app_name="aurora", user_id=session_id, session_id=session_id
        )

    async def pending(self, session_id: str) -> list[dict]:
        session = await self.get_session(session_id)
        result = []
        seen = set()
        for event in session.events:
            for call in event.get_function_calls():
                if (
                    call.name != "adk_request_confirmation"
                    or call.id in seen
                    or self.store.decided(call.id)
                ):
                    continue
                seen.add(call.id)
                original = call.args["originalFunctionCall"]
                details = dict(original.get("args", {}))
                if original["name"] == "reservar_area":
                    area = self.store.area(details.get("area", ""))
                    if area:
                        details["taxa"] = area["taxa"]
                result.append(
                    {
                        "id": call.id,
                        "acao": original["name"],
                        "detalhes": details,
                        "_original": original,
                        "_invocation": event.invocation_id,
                    }
                )
        return result

    async def response(self, session_id: str, text: str) -> dict:
        pending = await self.pending(session_id)
        return {
            "resposta": text,
            "confirmacoes_pendentes": [
                {key: value for key, value in p.items() if not key.startswith("_")}
                for p in pending
            ],
        }

    async def run(
        self, session_id: str, content: types.Content, invocation_id=None
    ) -> dict:
        runner = self.get_runner()
        texts = []
        async for event in runner.run_async(
            user_id=session_id,
            session_id=session_id,
            new_message=content,
            invocation_id=invocation_id,
            run_config=RunConfig(max_llm_calls=15),
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text and not part.thought and event.author != "user":
                        texts.append(part.text)
        response = await self.response(session_id, "\n".join(texts))
        if response["confirmacoes_pendentes"] and not response["resposta"]:
            response["resposta"] = "Aguardando sua decisão na rota de confirmações."
        return response

    async def message(self, session_id: str, text: str) -> dict:
        async with self.locks[session_id]:
            if await self.pending(session_id):
                return await self.response(
                    session_id,
                    "Responda primeiro à confirmação pendente pela rota própria.",
                )
            return await self.run(
                session_id, types.Content(role="user", parts=[types.Part(text=text)])
            )

    async def confirm(
        self, session_id: str, confirmation_id: str, approved: bool
    ) -> dict | None:
        async with self.locks[session_id]:
            pending = next(
                (
                    x
                    for x in await self.pending(session_id)
                    if x["id"] == confirmation_id
                ),
                None,
            )
            if pending is None:
                return None
            self.get_runner()  # Configuration failure must not consume consent.
            if not self.store.decide(
                confirmation_id, session_id, approved, pending["_original"]
            ):
                return None
            content = types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=confirmation_id,
                            name="adk_request_confirmation",
                            response={"confirmed": approved},
                        )
                    )
                ],
            )
            return await self.run(session_id, content, pending["_invocation"])

    async def close(self):
        await self.sessions.close()
