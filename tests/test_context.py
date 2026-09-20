import json

import httpx
from pydantic import PrivateAttr

from aurora.api import create_app
from tests.fake_model import ScriptedModel
from tests.test_api import command, session


class RecordingModel(ScriptedModel):
    _requests: list = PrivateAttr(default_factory=list)

    async def generate_content_async(self, llm_request, stream=False):
        self._requests.append(
            {
                "tools": set(llm_request.tools_dict),
                "contents": json.dumps(
                    [c.model_dump(mode="json") for c in llm_request.contents],
                    ensure_ascii=False,
                ),
                "instructions": str(llm_request.config.system_instruction),
            }
        )
        async for response in super().generate_content_async(llm_request, stream):
            yield response


async def test_new_turn_cannot_reuse_previous_operational_values(settings):
    model = RecordingModel()
    app = create_app(settings, model=model)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        sid = await session(client)
        first = await command(client, sid, "minhas_reservas")
        assert "RSV-1377" in first["resposta"]
        await command(
            client, sid, "consultar_regulamento", {"topico": "piscina"}, "regulamento"
        )
        # Another authorized operation changed the DB after the first read.
        app.state.runtime.store.cancel("101", "quadra", "2030-03-09")
        start = len(model._requests)
        final = await command(client, sid, "minhas_reservas")
        requests = model._requests[start:]
        assert all("RSV-1377" not in request["contents"] for request in requests)
        assert all(
            "Capítulo IV: Piscina" not in request["contents"] for request in requests
        )
        assert all(
            "Apartamento autenticado: 101." in request["instructions"]
            for request in requests
        )
        assert json.loads(final["resposta"])["reservas"] == []
        history = (await client.get(f"/sessoes/{sid}/eventos")).json()
        assert "RSV-1377" in json.dumps(history)
        assert "Capítulo IV: Piscina" in json.dumps(history, ensure_ascii=False)
    await app.state.runtime.close()
