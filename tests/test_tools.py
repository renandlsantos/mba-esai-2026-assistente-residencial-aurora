from types import SimpleNamespace

from aurora.agents import build_app
from aurora.store import Store
from tests.fake_model import ScriptedModel


def test_approved_flag_without_route_decision_cannot_write(settings):
    store = Store(settings)
    store.add_session("s1", "101")
    app = build_app(store, settings, ScriptedModel())
    context = SimpleNamespace(
        session=SimpleNamespace(id="s1"),
        function_call_id="invented",
        tool_confirmation=SimpleNamespace(confirmed=True),
    )
    reserve = next(
        tool
        for tool in app.root_agent.sub_agents[0].tools
        if getattr(tool, "name", "") == "reservar_area"
    )
    visitor = next(
        tool
        for tool in app.root_agent.sub_agents[1].tools
        if getattr(tool, "name", "") == "autorizar_visitante"
    )
    assert (
        reserve.func("salao-de-festas", "2030-06-01", context)["status"]
        == "confirmacao_obrigatoria"
    )
    assert (
        visitor.func("Pessoa", "2030-06-01", context)["status"]
        == "confirmacao_obrigatoria"
    )
    assert len(store.reservations("101")) == 1
    assert not store.visitors("101")


def test_decision_binds_original_arguments_and_session(settings):
    store = Store(settings)
    store.add_session("s1", "101")
    store.add_session("s2", "201")
    original = {
        "id": "call1",
        "name": "reservar_area",
        "args": {"area": "salao-de-festas", "data": "2030-06-01"},
    }
    assert store.decide("confirmation", "s1", True, original)
    assert store.approved("s1", "call1", "reservar_area", original["args"])
    assert not store.approved("s2", "call1", "reservar_area", original["args"])
    assert not store.approved(
        "s1", "call1", "reservar_area", {"area": "churrasqueira", "data": "2030-06-01"}
    )
    assert not store.approved("s1", "call2", "reservar_area", original["args"])
