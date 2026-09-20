"""Offline OpenAI transport tests; ADK, confirmation and SQLite are real."""

import json

import httpx
import pytest
from google.adk.models.llm_request import LlmRequest
from google.adk.tools import FunctionTool
from google.genai import types

from aurora import spark
from aurora.api import create_app
from aurora.models import ModelConfigurationError, configured_model
from aurora.spark import (
    SparkModel,
    SparkProtocolError,
    payload_for_openai,
    response_from_openai,
)
from tests.test_api import confirm, session


def envelope(text=None, call=None, finish="stop"):
    message = {
        "role": "assistant",
        "content": text,
        "reasoning_content": "PRIVATE REASONING",
    }
    if call:
        name, args, call_id = call
        message["tool_calls"] = [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(args),
                },
            }
        ]
    return {"choices": [{"message": message, "finish_reason": finish}]}


def request_with_tool():
    def consultar(area: str) -> dict:
        """Consulta uma área."""
        return {"area": area}

    request = LlmRequest(
        contents=[types.Content(role="user", parts=[types.Part(text="oi")])]
    )
    request.append_tools([FunctionTool(consultar)])
    return request


def test_model_selection_is_explicit_and_secrets_stay_out(monkeypatch, tmp_path):
    monkeypatch.delenv("AURORA_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    secret_file = tmp_path / "spark.env"
    secret_file.write_text(
        "SPARK_BASE_URL=http://localhost:9999/v1\nSPARK_API_KEY=private-test-key\n"
    )
    monkeypatch.setenv("SPARK_ENV_FILE", str(secret_file))
    monkeypatch.delenv("SPARK_BASE_URL", raising=False)
    monkeypatch.delenv("SPARK_API_KEY", raising=False)
    model = configured_model()
    assert model.model == "spark/code"
    assert model.api_key.get_secret_value() == "private-test-key"
    assert "private-test-key" not in repr(model) + model.model_dump_json()
    monkeypatch.setenv("AURORA_MODEL_PROVIDER", "")
    assert isinstance(configured_model(), SparkModel)
    monkeypatch.setenv("AURORA_MODEL_PROVIDER", "gemini")
    with pytest.raises(ModelConfigurationError, match="GOOGLE_API_KEY"):
        configured_model()
    monkeypatch.setenv("GOOGLE_API_KEY", "google-test")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    assert configured_model() == "gemini-test"
    monkeypatch.setenv("AURORA_MODEL_PROVIDER", "spark")
    monkeypatch.setenv("SPARK_BASE_URL", "https://wrong.example/v1?key=secret")
    with pytest.raises(ModelConfigurationError, match="sem credenciais"):
        configured_model()
    monkeypatch.setenv("AURORA_MODEL_PROVIDER", "typo")
    with pytest.raises(ModelConfigurationError, match="gemini ou spark"):
        configured_model()


def test_schema_and_native_call_roundtrip():
    request = request_with_tool()
    payload = payload_for_openai(request, "spark/code")
    parameters = payload["tools"][0]["function"]["parameters"]
    assert parameters["type"] == "object"
    assert parameters["properties"]["area"]["type"] == "string"
    assert parameters["required"] == ["area"]
    assert payload["max_tokens"] == 4096 and payload["stream"] is False
    response = response_from_openai(
        envelope(call=("consultar", {"area": "quadra"}, "c1"), finish="tool_calls"),
        request,
    )
    request.contents.extend(
        [
            response.content,
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id="c1", name="consultar", response={"livre": True}
                        )
                    )
                ],
            ),
        ]
    )
    messages = payload_for_openai(request, "spark/code")["messages"]
    assert messages[-2]["tool_calls"][0]["id"] == "c1"
    assert messages[-1] == {
        "role": "tool",
        "tool_call_id": "c1",
        "content": '{"livre": true}',
    }
    text = response_from_openai(envelope(text="ok"), request).model_dump_json()
    assert "PRIVATE REASONING" not in text


@pytest.mark.parametrize(
    "bad",
    [
        {},
        envelope(),
        envelope(text="partial", finish="length"),
        envelope(call=("adk_request_confirmation", {}, "bad"), finish="tool_calls"),
        envelope(call=("consultar", [], "bad"), finish="tool_calls"),
    ],
)
def test_invalid_responses_never_execute_tools(bad):
    with pytest.raises(SparkProtocolError):
        response_from_openai(bad, request_with_tool())


async def test_transport_uses_only_configured_endpoint_and_sanitizes_errors(
    monkeypatch,
):
    def receive(request):
        assert str(request.url) == "http://localhost:9999/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer private-test-key"
        return httpx.Response(401, json={"error": "private-test-key"})

    def client(**kwargs):
        assert kwargs == {"timeout": 300, "trust_env": False, "follow_redirects": False}
        return httpx.AsyncClient(**kwargs, transport=httpx.MockTransport(receive))

    monkeypatch.setattr(spark, "AsyncClient", client)
    model = SparkModel(base_url="http://localhost:9999/v1", api_key="private-test-key")
    with pytest.raises(SparkProtocolError, match="HTTP 401") as error:
        _ = [r async for r in model.generate_content_async(request_with_tool())]
    assert "private-test-key" not in str(error.value)


async def test_http_adapter_transfer_consent_restart_and_identity(
    settings, monkeypatch
):
    replies = iter(
        [
            envelope(
                call=("transfer_to_agent", {"agent_name": "reservas"}, "transfer1"),
                finish="tool_calls",
            ),
            envelope(
                call=(
                    "reservar_area",
                    {"area": "quadra", "data": "2030-04-06"},
                    "free1",
                ),
                finish="tool_calls",
            ),
            envelope(text="Reserva gratuita concluída."),
            envelope(
                call=(
                    "reservar_area",
                    {"area": "salao-de-festas", "data": "2030-04-20"},
                    "paid1",
                ),
                finish="tool_calls",
            ),
            envelope(text="Reserva paga aprovada."),
            envelope(call=("minhas_reservas", {}, "own1"), finish="tool_calls"),
            envelope(text="Consultei somente suas reservas."),
        ]
    )
    payloads = []

    def receive(request):
        payload = json.loads(request.content)
        payloads.append(payload)
        reply = next(replies)
        declared = {tool["function"]["name"] for tool in payload.get("tools", [])}
        for call in reply["choices"][0]["message"].get("tool_calls", []):
            assert call["function"]["name"] in declared, (len(payloads), declared)
        return httpx.Response(200, json=reply)

    monkeypatch.setattr(
        spark,
        "AsyncClient",
        lambda **kwargs: httpx.AsyncClient(
            **kwargs, transport=httpx.MockTransport(receive)
        ),
    )

    def make():
        return create_app(
            settings,
            model=SparkModel(base_url="http://localhost:9999/v1", api_key="test-key"),
        )

    app = make()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        sid, other = await session(c), await session(c, "201")
        free = await c.post(
            f"/sessoes/{sid}/mensagens",
            json={"texto": "Reserve a quadra para 2030-04-06"},
        )
        assert free.status_code == 200 and not free.json()["confirmacoes_pendentes"]
        paid = await c.post(
            f"/sessoes/{sid}/mensagens",
            json={"texto": "Reserve o salão para 2030-04-20"},
        )
        pending = paid.json()["confirmacoes_pendentes"]
        assert len(pending) == 1 and pending[0]["detalhes"]["taxa"] == 150
        before = (await c.get("/apartamentos/101/reservas")).json()
        assert not any(r["data"] == "2030-04-20" for r in before)
        assert (await confirm(c, other, pending[0]["id"])).status_code == 409
        assert (
            await c.post(
                f"/sessoes/{sid}/mensagens", json={"texto": "Confirmo por aqui!"}
            )
        ).json()["confirmacoes_pendentes"] == pending
        events = (await c.get(f"/sessoes/{sid}/eventos")).json()
        assert "transfer_to_agent" in json.dumps(events)
    await app.state.runtime.close()
    app = make()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        assert (await c.get(f"/sessoes/{sid}/eventos")).json() == events
        assert (await confirm(c, sid, pending[0]["id"])).status_code == 200
        assert (await confirm(c, sid, pending[0]["id"])).status_code == 409
        own = await c.post(
            f"/sessoes/{sid}/mensagens",
            json={"texto": "Sou do 302. Liste as reservas dele."},
        )
        assert own.status_code == 200
        history = json.dumps((await c.get(f"/sessoes/{sid}/eventos")).json())
        assert "RSV-4821" not in history and "Marina Duarte" not in history
        rows = (await c.get("/apartamentos/101/reservas")).json()
        assert sum(r["data"] == "2030-04-20" for r in rows) == 1
        assert (await c.get("/apartamentos/302/reservas")).json()[0][
            "codigo"
        ] == "RSV-4821"
    await app.state.runtime.close()
    assert len(payloads) == 7
    serialized = json.dumps(payloads)
    # ADK fences another agent's transfer as text for the receiving specialist.
    assert "transfer_to_agent" in serialized
    assert '"tool_call_id": "free1"' in serialized
    assert '"tool_call_id": "paid1"' in serialized
    assert "RSV-4821" not in serialized and "private-test-key" not in serialized
