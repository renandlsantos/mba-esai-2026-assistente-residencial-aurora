from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from .config import Settings
from .models import ModelConfigurationError
from .runtime import Runtime


class Request(BaseModel):
    model_config = ConfigDict(extra="forbid")


class NewSession(Request):
    apartamento: str = Field(min_length=1, max_length=30)


class Message(Request):
    texto: str = Field(min_length=1, max_length=20000)


class Confirmation(Request):
    id: str = Field(min_length=1, max_length=300)
    confirmado: StrictBool


def create_app(settings: Settings | None = None, *, model=None) -> FastAPI:
    runtime = Runtime(settings or Settings(Path.cwd()), model=model)

    @asynccontextmanager
    async def lifespan(app):
        yield
        await runtime.close()

    app = FastAPI(title="Residencial Aurora", lifespan=lifespan)
    app.state.runtime = runtime

    def require_session(session_id: str):
        if runtime.store.apartment(session_id) is None:
            raise HTTPException(404, "Sessão não encontrada.")

    @app.post("/sessoes", status_code=201)
    async def new_session(body: NewSession):
        if not runtime.store.apartment_exists(body.apartamento):
            raise HTTPException(
                422,
                "Apartamento não encontrado. Execute restore antes do primeiro uso.",
            )
        return {"session_id": await runtime.create_session(body.apartamento)}

    @app.post("/sessoes/{session_id}/mensagens")
    async def message(session_id: str, body: Message):
        require_session(session_id)
        try:
            return await runtime.message(session_id, body.texto)
        except ModelConfigurationError as exc:
            raise HTTPException(503, str(exc)) from exc

    @app.post("/sessoes/{session_id}/confirmacoes")
    async def confirmation(session_id: str, body: Confirmation):
        require_session(session_id)
        try:
            result = await runtime.confirm(session_id, body.id, body.confirmado)
        except ModelConfigurationError as exc:
            raise HTTPException(503, str(exc)) from exc
        if result is None:
            raise HTTPException(409, "Confirmação não pendente nesta sessão.")
        return result

    @app.get("/sessoes/{session_id}/eventos")
    async def events(session_id: str):
        require_session(session_id)
        session = await runtime.get_session(session_id)
        return [event.model_dump(mode="json") for event in session.events]

    @app.get("/apartamentos/{apartamento}/reservas")
    async def reservations(apartamento: str):
        return runtime.store.reservations(apartamento)

    @app.get("/apartamentos/{apartamento}/visitantes")
    async def visitors(apartamento: str):
        return runtime.store.visitors(apartamento)

    return app
