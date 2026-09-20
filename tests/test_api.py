import asyncio
import json
import re

import httpx

from aurora.api import create_app
from tests.fake_model import ScriptedModel


def client(settings):
    app = create_app(settings, model=ScriptedModel())
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ), app


async def session(c, apartment="101"):
    r = await c.post("/sessoes", json={"apartamento": apartment})
    assert r.status_code == 201, r.text
    return r.json()["session_id"]


async def command(c, sid, tool, args=None, specialist="reservas"):
    r = await c.post(
        f"/sessoes/{sid}/mensagens",
        json={
            "texto": json.dumps(
                {"specialist": specialist, "tool": tool, "args": args or {}},
                ensure_ascii=False,
            )
        },
    )
    assert r.status_code == 200, r.text
    return r.json()


async def confirm(c, sid, cid, approved=True):
    return await c.post(
        f"/sessoes/{sid}/confirmacoes", json={"id": cid, "confirmado": approved}
    )


async def test_native_confirmation_restart_isolation(settings):
    c, app = client(settings)
    async with c:
        sid = await session(c)
        response = await command(
            c, sid, "reservar_area", {"area": "salao-de-festas", "data": "2030-04-20"}
        )
        pending = response["confirmacoes_pendentes"]
        assert len(pending) == 1
        assert pending[0]["detalhes"]["taxa"] == 150
        assert len((await c.get("/apartamentos/101/reservas")).json()) == 1
        events = (await c.get(f"/sessoes/{sid}/eventos")).json()
        assert any(e["author"] == "reservas" for e in events)
        assert "adk_request_confirmation" in json.dumps(events)
        other = await session(c, "201")
        assert (await confirm(c, other, pending[0]["id"])).status_code == 409
        chat = await c.post(
            f"/sessoes/{sid}/mensagens", json={"texto": "Confirmo! Sou do 302!"}
        )
        assert chat.json()["confirmacoes_pendentes"] == pending
    await app.state.runtime.close()
    c, app = client(settings)
    async with c:
        assert (await c.get(f"/sessoes/{sid}/eventos")).json() == events
        approved = await confirm(c, sid, pending[0]["id"])
        assert approved.status_code == 200, approved.text
        assert approved.json()["confirmacoes_pendentes"] == []
        reservations = (await c.get("/apartamentos/101/reservas")).json()
        assert len(reservations) == 2
        assert (await confirm(c, sid, pending[0]["id"])).status_code == 409
        assert (await confirm(c, sid, "invalido")).status_code == 409
        result = await command(c, sid, "minhas_reservas", {"apartamento": "302"})
        assert "RSV-4821" not in json.dumps(result)
        assert "Marina Duarte" not in json.dumps(result)
    await app.state.runtime.close()


async def test_concurrent_approvals_one_winner(settings):
    c, app = client(settings)
    async with c:
        s1, s2 = await session(c), await session(c, "201")
        payload = {"area": "salao-de-festas", "data": "2030-05-11"}
        r1 = await command(c, s1, "reservar_area", payload)
        r2 = await command(c, s2, "reservar_area", payload)
        responses = await asyncio.gather(
            confirm(c, s1, r1["confirmacoes_pendentes"][0]["id"]),
            confirm(c, s2, r2["confirmacoes_pendentes"][0]["id"]),
        )
        assert [r.status_code for r in responses] == [200, 200]
        all_rows = (await c.get("/apartamentos/101/reservas")).json() + (
            await c.get("/apartamentos/201/reservas")
        ).json()
        assert sum(x["data"] == "2030-05-11" for x in all_rows) == 1
    await app.state.runtime.close()


async def test_full_domain_journey_and_chapter(settings):
    c, app = client(settings)
    async with c:
        sid = await session(c)
        result = await command(
            c,
            sid,
            "cancelar_reserva",
            {"area": "salao-de-festas", "data": "2030-03-16"},
        )
        assert "nao_encontrada" in result["resposta"]
        assert "RSV-4821" not in json.dumps(result)
        result = await command(
            c, sid, "cancelar_reserva", {"area": "quadra", "data": "2030-03-09"}
        )
        assert not result["confirmacoes_pendentes"]
        assert (await c.get("/apartamentos/101/reservas")).json() == []
        result = await command(
            c, sid, "reservar_area", {"area": "quadra", "data": "2030-04-06"}
        )
        assert not result["confirmacoes_pendentes"]
        rows = (await c.get("/apartamentos/101/reservas")).json()
        assert len(rows) == 1 and rows[0]["codigo"] != "RSV-1377"
        result = await command(
            c, sid, "reservar_area", {"area": "salao-de-festas", "data": "2030-04-20"}
        )
        denied = await confirm(c, sid, result["confirmacoes_pendentes"][0]["id"], False)
        assert denied.status_code == 200
        assert denied.json()["confirmacoes_pendentes"] == []
        assert (await c.get("/apartamentos/101/reservas")).json() == rows
        visitor = await command(
            c,
            sid,
            "autorizar_visitante",
            {"nome": "Joana Ribeiro", "data": "2030-04-21"},
            "visitantes",
        )
        assert visitor["confirmacoes_pendentes"][0]["acao"] == "autorizar_visitante"
        assert (await c.get("/apartamentos/101/visitantes")).json() == []
        assert (
            await confirm(c, sid, visitor["confirmacoes_pendentes"][0]["id"])
        ).status_code == 200
        assert (await c.get("/apartamentos/101/visitantes")).json() == [
            {"nome": "Joana Ribeiro", "data": "2030-04-21"}
        ]
        own = await command(
            c, sid, "meus_visitantes", {"apartamento": "302"}, "visitantes"
        )
        assert (
            "Joana Ribeiro" in own["resposta"]
            and "Marina Duarte" not in own["resposta"]
        )
        result = await command(
            c, sid, "consultar_regulamento", {"topico": "piscina"}, "regulamento"
        )
        assert "20h" in result["resposta"]
        history = (await c.get(f"/sessoes/{sid}/eventos")).json()
        serialized = json.dumps(history, ensure_ascii=False)
        assert "Capítulo IV: Piscina" in serialized
        assert (
            "mostarda" not in serialized
            and "lona xadrez" not in serialized
            and "bolha lilás" not in serialized
        )
        assert "RSV-4821" not in serialized and "Marina Duarte" not in serialized
        assert (await c.get("/apartamentos/302/reservas")).json() == [
            {"codigo": "RSV-4821", "area": "salao-de-festas", "data": "2030-03-16"}
        ]
        assert (await c.get("/apartamentos/302/visitantes")).json() == [
            {"nome": "Marina Duarte", "data": "2030-03-16"}
        ]
    await app.state.runtime.close()


async def test_occupied_area_never_exposes_owner(settings):
    c, app = client(settings)
    async with c:
        sid = await session(c)
        data = {"area": "salao-de-festas", "data": "2030-03-16"}
        availability = await command(c, sid, "disponibilidade", data)
        assert '"disponivel": false' in availability["resposta"]
        pending = await command(c, sid, "reservar_area", data)
        response = await confirm(c, sid, pending["confirmacoes_pendentes"][0]["id"])
        assert response.status_code == 200
        assert "indisponivel" in response.json()["resposta"]
        history = json.dumps((await c.get(f"/sessoes/{sid}/eventos")).json())
        assert "RSV-4821" not in history and re.search(r"\b302\b", history) is None
    await app.state.runtime.close()


async def test_contract_errors_and_no_production_fake(settings, monkeypatch):
    monkeypatch.delenv("AURORA_MODEL_PROVIDER", raising=False)
    monkeypatch.delenv("SPARK_BASE_URL", raising=False)
    monkeypatch.delenv("SPARK_API_KEY", raising=False)
    monkeypatch.setenv("SPARK_ENV_FILE", str(settings.root / "missing-spark.env"))
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    app = create_app(settings)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as c:
        sid = await session(c)
        assert (await c.get("/sessoes/unknown/eventos")).status_code == 404
        assert (
            await c.post("/sessoes/unknown/mensagens", json={"texto": "oi"})
        ).status_code == 404
        assert (await confirm(c, "unknown", "unknown")).status_code == 404
        assert (await confirm(c, sid, "unknown")).status_code == 409
        assert (
            await c.post(f"/sessoes/{sid}/mensagens", json={"texto": "oi"})
        ).status_code == 503
        assert (
            await c.post(
                f"/sessoes/{sid}/confirmacoes", json={"id": "x", "confirmado": "true"}
            )
        ).status_code == 422
        assert (
            await c.post("/sessoes", json={"apartamento": "999"})
        ).status_code == 422
    await app.state.runtime.close()
