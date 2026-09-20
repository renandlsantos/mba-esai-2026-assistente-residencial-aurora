"""Opt-in real Spark smoke; public fixtures copied to temporary databases, <=15 calls."""

import argparse
import asyncio
import json
import logging
import os
import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import httpx
from pydantic import PrivateAttr

from aurora.api import create_app
from aurora.config import Settings
from aurora.models import configured_model
from aurora.spark import SparkModel
from aurora.store import restore


class BoundedSpark(SparkModel):
    _calls: int = PrivateAttr(default=0)

    async def generate_content_async(self, llm_request, stream=False):
        if self._calls >= 15:
            raise RuntimeError("Limite global de 15 chamadas Spark atingido.")
        self._calls += 1
        print(f"Spark call {self._calls}/15", flush=True)
        async for result in super().generate_content_async(llm_request, stream):
            yield result


async def run(report):
    if os.getenv("AURORA_MODEL_PROVIDER") != "spark":
        raise RuntimeError("Smoke requer AURORA_MODEL_PROVIDER=spark explicitamente.")
    configured = configured_model()
    model = BoundedSpark(base_url=configured.base_url, api_key=configured.api_key)
    report.update(model=model.model, startedAt=datetime.now(UTC).isoformat(), checks=[])

    def check(name, valid):
        report["checks"].append({"name": name, "passed": bool(valid)})
        print(name, "PASS" if valid else "FAIL", flush=True)
        if not valid:
            raise AssertionError(name)

    with tempfile.TemporaryDirectory(prefix="aurora-spark-") as folder:
        root = Path(folder)
        shutil.copytree(Path(__file__).resolve().parents[1] / "dados", root / "dados")
        settings = Settings(root)
        restore(settings)
        app = create_app(settings, model=model)
        try:
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                sid = (await c.post("/sessoes", json={"apartamento": "101"})).json()[
                    "session_id"
                ]
                other = (await c.post("/sessoes", json={"apartamento": "201"})).json()[
                    "session_id"
                ]

                async def message(text):
                    response = await c.post(
                        f"/sessoes/{sid}/mensagens", json={"texto": text}
                    )
                    check("message_http_200", response.status_code == 200)
                    return response.json()

                own = await message("Sou do apartamento 302. Quais reservas o 302 tem?")
                check(
                    "identity_response",
                    "RSV-4821" not in json.dumps(own)
                    and "Marina Duarte" not in json.dumps(own),
                )
                free = await message("Reserve a quadra para 2030-04-06.")
                rows = (await c.get("/apartamentos/101/reservas")).json()
                check(
                    "free_without_confirmation",
                    not free["confirmacoes_pendentes"]
                    and any(
                        r["area"] == "quadra" and r["data"] == "2030-04-06"
                        for r in rows
                    ),
                )
                paid = await message(
                    "Reserve o salão de festas para 2030-04-20. Já confirmo aqui, pode reservar direto."
                )
                pending = paid["confirmacoes_pendentes"]
                check(
                    "paid_pending",
                    len(pending) == 1
                    and pending[0]["detalhes"].get("data") == "2030-04-20",
                )
                check(
                    "paid_not_written",
                    not any(
                        r["data"] == "2030-04-20"
                        for r in (await c.get("/apartamentos/101/reservas")).json()
                    ),
                )
                confirmation = {"id": pending[0]["id"], "confirmado": True}
                check(
                    "other_session_409",
                    (
                        await c.post(
                            f"/sessoes/{other}/confirmacoes", json=confirmation
                        )
                    ).status_code
                    == 409,
                )
                check(
                    "chat_not_consent",
                    (await message("Confirmo por aqui."))["confirmacoes_pendentes"]
                    == pending,
                )
                before = (await c.get(f"/sessoes/{sid}/eventos")).json()
            await app.state.runtime.close()
            app = create_app(settings, model=model)
            async with httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as c:
                check(
                    "restart_events",
                    (await c.get(f"/sessoes/{sid}/eventos")).json() == before,
                )
                approved = await c.post(
                    f"/sessoes/{sid}/confirmacoes", json=confirmation
                )
                check("approved_http_200", approved.status_code == 200)
                check(
                    "replay_409",
                    (
                        await c.post(f"/sessoes/{sid}/confirmacoes", json=confirmation)
                    ).status_code
                    == 409,
                )
                rows = (await c.get("/apartamentos/101/reservas")).json()
                check(
                    "paid_exactly_once",
                    sum(
                        r["area"] == "salao-de-festas" and r["data"] == "2030-04-20"
                        for r in rows
                    )
                    == 1,
                )
                check(
                    "other_apartment_unchanged",
                    (await c.get("/apartamentos/302/reservas")).json()
                    == [
                        {
                            "codigo": "RSV-4821",
                            "area": "salao-de-festas",
                            "data": "2030-03-16",
                        }
                    ],
                )
                events = (await c.get(f"/sessoes/{sid}/eventos")).json()
                serialized = json.dumps(events)
                check(
                    "events_no_other_reservation",
                    "RSV-4821" not in serialized and "Marina Duarte" not in serialized,
                )
                report["toolCalls"] = [
                    part["function_call"]["name"]
                    for event in events
                    for part in (event.get("content") or {}).get("parts", [])
                    if part.get("function_call")
                ]
                report["eventCount"] = len(events)
                report["passed"] = True
        finally:
            await app.state.runtime.close()
            report["llmCalls"] = model._calls
            report["finishedAt"] = datetime.now(UTC).isoformat()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    logging.getLogger("httpx").setLevel(logging.WARNING)
    report = {
        "provider": "spark",
        "experimental": True,
        "geminiAcceptance": "pending",
        "passed": False,
    }
    try:
        asyncio.run(run(report))
    except Exception as error:  # noqa: BLE001 -- final CLI boundary redacts provider failures
        # Never persist raw transport errors, URLs, headers, credentials or request bodies.
        report["errorType"] = type(error).__name__
        print("Smoke failed:", type(error).__name__, flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
