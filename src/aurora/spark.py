"""Experimental text/tool adapter for the explicitly configured local Spark server."""

import json

import httpx
from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types
from httpx import AsyncClient
from pydantic import Field, SecretStr


class SparkProtocolError(RuntimeError):
    pass


def schema_for_openai(value):
    if isinstance(value, list):
        return [schema_for_openai(item) for item in value]
    if not isinstance(value, dict):
        return value
    return {
        key: item.lower()
        if key == "type" and isinstance(item, str)
        else schema_for_openai(item)
        for key, item in value.items()
    }


def messages_for_openai(request):
    messages = []
    instruction = request.config.system_instruction
    if instruction:
        if not isinstance(instruction, str):
            raise SparkProtocolError("Spark experimental aceita instruções textuais.")
        messages.append({"role": "system", "content": instruction})
    for content in request.contents:
        texts, calls, responses = [], [], []
        for part in content.parts or []:
            if part.thought:
                continue
            if part.text is not None:
                texts.append(part.text)
            elif call := part.function_call:
                if not call.id or not call.name:
                    raise SparkProtocolError("Chamada de ferramenta sem identidade.")
                calls.append(
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.name,
                            "arguments": json.dumps(
                                call.args or {}, ensure_ascii=False
                            ),
                        },
                    }
                )
            elif result := part.function_response:
                if not result.id:
                    raise SparkProtocolError("Resultado de ferramenta sem identidade.")
                responses.append(
                    {
                        "role": "tool",
                        "tool_call_id": result.id,
                        "content": json.dumps(result.response, ensure_ascii=False),
                    }
                )
            else:
                raise SparkProtocolError(
                    "Spark experimental suporta apenas texto e ferramentas."
                )
        if texts or calls:
            message = {
                "role": "assistant" if content.role == "model" else "user",
                "content": "\n".join(texts) or None,
            }
            if calls:
                message["tool_calls"] = calls
            messages.append(message)
        messages.extend(responses)
    return messages


def payload_for_openai(request, model):
    tools = []
    for tool in request.config.tools or []:
        if not isinstance(tool, types.Tool) or not tool.function_declarations:
            raise SparkProtocolError("Spark experimental aceita somente FunctionTools.")
        for declaration in tool.function_declarations:
            parameters = declaration.parameters_json_schema
            if parameters is None:
                parameters = (
                    declaration.parameters.model_dump(mode="json", exclude_none=True)
                    if declaration.parameters
                    else {"type": "object", "properties": {}}
                )
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": declaration.name,
                        "description": declaration.description or "",
                        "parameters": schema_for_openai(parameters),
                    },
                }
            )
    payload = {
        "model": model,
        "messages": messages_for_openai(request),
        "stream": False,
        "temperature": 0,
        "max_tokens": 4096,
    }
    if tools:
        payload.update(tools=tools, tool_choice="auto")
    return payload


def response_from_openai(data, request):
    try:
        choice = data["choices"][0]
        message = choice["message"]
        if choice["finish_reason"] not in {"stop", "tool_calls"}:
            raise SparkProtocolError(
                "Spark não concluiu a resposta; nenhuma ferramenta foi executada."
            )
        if message["role"] != "assistant":
            raise SparkProtocolError("Resposta Spark com papel inválido.")
        parts = []
        text = message.get("content")
        if text is not None and not isinstance(text, str):
            raise SparkProtocolError("Resposta Spark não textual.")
        if text:
            parts.append(types.Part(text=text))
        ids = set()
        for call in message.get("tool_calls") or []:
            name, call_id = call["function"]["name"], call["id"]
            arguments = json.loads(call["function"]["arguments"])
            if (
                call["type"] != "function"
                or not isinstance(call_id, str)
                or not call_id
                or call_id in ids
                or name not in request.tools_dict
                or not isinstance(arguments, dict)
            ):
                raise SparkProtocolError("Resposta Spark contém ferramenta inválida.")
            ids.add(call_id)
            parts.append(
                types.Part(
                    function_call=types.FunctionCall(
                        id=call_id, name=name, args=arguments
                    )
                )
            )
        if not parts:
            raise SparkProtocolError("Spark retornou resposta vazia.")
        return LlmResponse(
            content=types.Content(role="model", parts=parts),
            finish_reason=types.FinishReason.STOP,
        )
    except (KeyError, IndexError, TypeError, ValueError):
        raise SparkProtocolError("Resposta Spark fora do protocolo esperado.") from None


class SparkModel(BaseLlm):
    model: str = "spark/code"
    base_url: str = Field(repr=False, exclude=True)
    api_key: SecretStr = Field(repr=False, exclude=True)

    async def generate_content_async(self, llm_request, stream=False):
        if stream:
            raise SparkProtocolError("Spark experimental não oferece streaming.")
        payload = payload_for_openai(llm_request, self.model)
        async with AsyncClient(
            timeout=300, trust_env=False, follow_redirects=False
        ) as client:
            try:
                response = await client.post(
                    self.base_url + "/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": "Bearer " + self.api_key.get_secret_value()
                    },
                )
            except httpx.HTTPError:
                raise SparkProtocolError(
                    "Falha de conexão/timeout com Spark."
                ) from None
        if not response.is_success:
            raise SparkProtocolError(f"Spark respondeu HTTP {response.status_code}.")
        try:
            data = response.json()
        except ValueError:
            raise SparkProtocolError("Spark retornou JSON inválido.") from None
        yield response_from_openai(data, llm_request)
