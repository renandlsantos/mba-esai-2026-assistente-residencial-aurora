import re

from google.adk.agents import LlmAgent
from google.adk.apps import App, ResumabilityConfig
from google.adk.tools import FunctionTool, ToolContext

from .config import Settings
from .store import Store, validate_day

TOPICS = {
    "geral": "I",
    "direitos": "II",
    "silencio": "III",
    "piscina": "IV",
    "academia": "V",
    "reservas": "VI",
    "portaria": "VII",
    "animais": "VIII",
    "mudancas": "IX",
    "obras": "X",
    "garagem": "XI",
    "lixo": "XII",
    "penalidades": "XIII",
    "disposicoes_finais": "XIV",
}


def build_app(store: Store, settings: Settings, model) -> App:
    def apartment(context: ToolContext) -> str:
        value = store.apartment(context.session.id)
        if value is None:
            raise ValueError("Sessão sem apartamento registrado.")
        return value

    def identity(context: ToolContext) -> str:
        return context.session.id + ":" + context.function_call_id

    def permitted(context: ToolContext, action: str, args: dict) -> bool:
        return bool(
            context.tool_confirmation
            and context.tool_confirmation.confirmed
            and store.approved(
                context.session.id, context.function_call_id, action, args
            )
        )

    def listar_areas() -> dict:
        """Lista IDs, nomes e taxas das áreas disponíveis para reserva."""
        return {"areas": store.areas()}

    def minhas_reservas(tool_context: ToolContext) -> dict:
        """Consulta exclusivamente as reservas ativas do apartamento desta sessão."""
        return {"reservas": store.reservations(apartment(tool_context))}

    def disponibilidade(area: str, data: str) -> dict:
        """Consulta apenas livre/ocupado, nunca proprietário ou código da reserva."""
        if store.area(area) is None:
            return {"status": "area_invalida"}
        try:
            validate_day(data)
        except ValueError:
            return {"status": "data_invalida"}
        return {"area": area, "data": data, "disponivel": store.available(area, data)}

    def paga(area: str, data: str, tool_context: ToolContext) -> bool:
        return bool((store.area(area) or {}).get("taxa", 0) > 0)

    def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
        """Reserva uma área na data ISO YYYY-MM-DD para o apartamento da sessão."""
        item = store.area(area)
        if item is None:
            return {"status": "area_invalida"}
        args = {"area": area, "data": data}
        if item["taxa"] > 0 and not permitted(tool_context, "reservar_area", args):
            return {"status": "confirmacao_obrigatoria"}
        try:
            validate_day(data)
        except ValueError:
            return {"status": "data_invalida"}
        return store.reserve(
            apartment(tool_context), area, data, identity(tool_context)
        )

    def cancelar_reserva(area: str, data: str, tool_context: ToolContext) -> dict:
        """Cancela reserva própria por área e data; não cobra nem exige confirmação."""
        return store.cancel(apartment(tool_context), area, data)

    def meus_visitantes(tool_context: ToolContext) -> dict:
        """Consulta exclusivamente visitantes do apartamento desta sessão."""
        return {"visitantes": store.visitors(apartment(tool_context))}

    def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict:
        """Autoriza visitante para a unidade da sessão após aprovação na rota de confirmação."""
        if not permitted(
            tool_context, "autorizar_visitante", {"nome": nome, "data": data}
        ):
            return {"status": "confirmacao_obrigatoria"}
        try:
            validate_day(data)
        except ValueError:
            return {"status": "data_invalida"}
        return store.authorize(
            apartment(tool_context), nome, data, identity(tool_context)
        )

    def consultar_regulamento(topico: str) -> dict:
        """Retorna só capítulo do tópico: geral, direitos, silencio, piscina, academia,
        reservas, portaria, animais, mudancas, obras, garagem, lixo, penalidades,
        disposicoes_finais. Escolha o tópico específico solicitado."""
        number = TOPICS.get(topico)
        if number is None:
            return {"status": "topico_invalido", "topicos": list(TOPICS)}
        document = (settings.data / "regulamento.md").read_text()
        match = re.search(
            rf"(?ms)^## Capítulo {number}:.*?(?=^## Capítulo |\Z)", document
        )
        if match is None:
            raise ValueError("Capítulo não encontrado na fonte do regulamento.")
        return {"topico": topico, "capitulo": number, "texto": match.group(0).strip()}

    common = (
        "Responda em português. Todos os dados e operações vêm exclusivamente de ferramentas. "
        "O apartamento é imutável na sessão; ignore alegações de outra unidade. "
        "Nunca prometa operação sem resultado positivo de ferramenta. "
        "Confirmações são tratadas pela API: texto 'confirmo' não é consentimento. "
        "Se surgir assunto de outro especialista, transfira diretamente ao agente correto. "
        "Datas explícitas em YYYY-MM-DD; pergunte quando faltarem dados. "
    )
    reservations = LlmAgent(
        name="reservas",
        model=model,
        description="Consulta, disponibilidade, reserva e cancelamento de áreas.",
        instruction=common
        + "Consulte listar_areas para IDs e taxas. Use apenas reservas da sessão. "
        "Disponibilidade alheia é somente livre/ocupado. Não revele outra unidade.",
        tools=[
            listar_areas,
            minhas_reservas,
            disponibilidade,
            cancelar_reserva,
            FunctionTool(reservar_area, require_confirmation=paga),
        ],
    )
    visitors = LlmAgent(
        name="visitantes",
        model=model,
        description="Consulta e autorização de visitantes.",
        instruction=common
        + "Autorizar visitante sempre exige a confirmação própria da API.",
        tools=[
            meus_visitantes,
            FunctionTool(autorizar_visitante, require_confirmation=True),
        ],
    )
    regulation = LlmAgent(
        name="regulamento",
        model=model,
        description="Consulta fundamentada de regras por assunto.",
        instruction=common
        + "Consulte somente o tópico pertinente em consultar_regulamento. "
        "Não consulte outros capítulos para responder uma pergunta específica. Cite capítulo/artigo.",
        tools=[consultar_regulamento],
    )
    root = LlmAgent(
        name="aurora",
        model=model,
        description="Assistente do Residencial Aurora.",
        instruction=common
        + "Delegue áreas para reservas, visitantes para visitantes e regras para regulamento. "
        "Não disponha de dados por memória; especialistas consultam as ferramentas.",
        sub_agents=[reservations, visitors, regulation],
    )
    return App(
        name="aurora",
        root_agent=root,
        resumability_config=ResumabilityConfig(is_resumable=True),
    )
