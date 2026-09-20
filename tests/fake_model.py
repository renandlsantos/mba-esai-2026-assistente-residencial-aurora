"""Modelo roteirizado EXCLUSIVO de testes; Runner, agentes, tools e SQL são reais."""

import json
from uuid import uuid4

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types


class ScriptedModel(BaseLlm):
    model: str = "offline-scripted-test"

    async def generate_content_async(self, llm_request, stream=False):
        command = next(
            (
                json.loads(part.text)
                for content in reversed(llm_request.contents)
                if content.role == "user"
                for part in content.parts or []
                if part.text and part.text.startswith('{"specialist"')
            ),
            None,
        )
        available = llm_request.tools_dict
        last = llm_request.contents[-1]
        results = [p.function_response for p in last.parts or [] if p.function_response]
        if results and results[-1].name != "transfer_to_agent":
            response = json.dumps(results[-1].response, ensure_ascii=False)
            yield LlmResponse(
                content=types.Content(role="model", parts=[types.Part(text=response)])
            )
            return
        if command and command["tool"] in available:
            call = types.FunctionCall(
                id="call-" + uuid4().hex,
                name=command["tool"],
                args=command.get("args", {}),
            )
        elif command:
            call = types.FunctionCall(
                id="transfer-" + uuid4().hex,
                name="transfer_to_agent",
                args={"agent_name": command["specialist"]},
            )
        else:
            yield LlmResponse(
                content=types.Content(
                    role="model", parts=[types.Part(text="Sem roteiro de teste.")]
                )
            )
            return
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(function_call=call)])
        )
