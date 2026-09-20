import json
import socket
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import httpx


@contextmanager
def server(settings):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    process = subprocess.Popen(
        [sys.executable, "-m", "tests.server", str(settings.root), str(port)],
        cwd=Path(__file__).parents[1],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    client = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=15)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise AssertionError(process.stderr.read().decode())
            try:
                if client.get("/openapi.json").status_code == 200:
                    break
            except httpx.ConnectError:
                pass
            time.sleep(0.05)
        else:
            raise AssertionError("Servidor de teste não iniciou.")
        yield client
    finally:
        client.close()
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        process.stderr.close()


def test_actual_process_restart_with_pending_visitor(settings):
    with server(settings) as client:
        sid = client.post("/sessoes", json={"apartamento": "101"}).json()["session_id"]
        command = {
            "specialist": "visitantes",
            "tool": "autorizar_visitante",
            "args": {"nome": "Joana Ribeiro", "data": "2030-04-21"},
        }
        response = client.post(
            f"/sessoes/{sid}/mensagens", json={"texto": json.dumps(command)}
        )
        assert response.status_code == 200, response.text
        confirmation_id = response.json()["confirmacoes_pendentes"][0]["id"]
        history = client.get(f"/sessoes/{sid}/eventos").json()
    with server(settings) as client:
        assert client.get(f"/sessoes/{sid}/eventos").json() == history
        response = client.post(
            f"/sessoes/{sid}/confirmacoes",
            json={"id": confirmation_id, "confirmado": True},
        )
        assert response.status_code == 200, response.text
        assert client.get("/apartamentos/101/visitantes").json() == [
            {"nome": "Joana Ribeiro", "data": "2030-04-21"}
        ]
        command = {"specialist": "visitantes", "tool": "meus_visitantes", "args": {}}
        response = client.post(
            f"/sessoes/{sid}/mensagens", json={"texto": json.dumps(command)}
        )
        assert "Joana Ribeiro" in response.json()["resposta"]
        assert len(client.get(f"/sessoes/{sid}/eventos").json()) > len(history)
        assert (
            client.post(
                f"/sessoes/{sid}/confirmacoes",
                json={"id": confirmation_id, "confirmado": True},
            ).status_code
            == 409
        )
