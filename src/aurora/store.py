import json
import sqlite3
from contextlib import contextmanager
from datetime import date
from uuid import uuid4

from .config import Settings

OWNER = "residencial-aurora-v1\n"


def validate_day(value: str) -> None:
    if date.fromisoformat(value).isoformat() != value:
        raise ValueError("Data deve usar YYYY-MM-DD.")


def ensure_owned(settings: Settings) -> None:
    folder = settings.runtime
    if folder.is_symlink() or folder.parent.is_symlink():
        raise ValueError("Diretório de runtime não pode ser link simbólico.")
    folder.mkdir(parents=True, exist_ok=True)
    marker = folder / "OWNER"
    if marker.is_symlink():
        raise ValueError("Marcador de propriedade inválido.")
    if not marker.exists():
        if list(folder.iterdir()):
            raise ValueError(
                "Runtime não vazio sem marcador Aurora; operação recusada."
            )
        marker.write_text(OWNER)
    if marker.read_text() != OWNER:
        raise ValueError("Runtime não pertence ao Aurora.")
    for name in ("domain.sqlite3", "adk.sqlite3"):
        for suffix in ("", "-wal", "-shm", "-journal"):
            if (folder / (name + suffix)).is_symlink():
                raise ValueError("Banco não pode ser link simbólico.")


def restore(settings: Settings) -> None:
    # Load and validate the source before touching the application's databases.
    data = {
        name: json.loads((settings.data / f"{name}.json").read_text())
        for name in ("apartamentos", "areas", "reservas", "visitantes")
    }
    ensure_owned(settings)
    for name in ("domain.sqlite3", "adk.sqlite3"):
        for suffix in ("", "-wal", "-shm", "-journal"):
            (settings.runtime / (name + suffix)).unlink(missing_ok=True)
    store = Store(settings)
    with store.connect() as db:
        db.executemany(
            "INSERT INTO apartamentos VALUES (?,?)",
            [(x["numero"], x["morador"]) for x in data["apartamentos"]],
        )
        db.executemany(
            "INSERT INTO areas VALUES (?,?,?)",
            [(x["id"], x["nome"], x["taxa"]) for x in data["areas"]],
        )
        db.executemany(
            "INSERT INTO reservas VALUES (?,?,?,?,1)",
            [
                (x["codigo"], x["apartamento"], x["area"], x["data"])
                for x in data["reservas"]
            ],
        )
        db.executemany(
            "INSERT INTO visitantes VALUES (?,?,?,?,?)",
            [
                (str(uuid4()), x["apartamento"], x["nome"], x["data"], None)
                for x in data["visitantes"]
            ],
        )


class Store:
    def __init__(self, settings: Settings):
        ensure_owned(settings)
        self.path = settings.domain_db
        with self.connect() as db:
            db.executescript("""
              CREATE TABLE IF NOT EXISTS apartamentos(numero TEXT PRIMARY KEY, morador TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS areas(id TEXT PRIMARY KEY, nome TEXT NOT NULL, taxa REAL NOT NULL);
              CREATE TABLE IF NOT EXISTS reservas(
                codigo TEXT PRIMARY KEY, apartamento TEXT NOT NULL REFERENCES apartamentos,
                area TEXT NOT NULL REFERENCES areas, data TEXT NOT NULL, ativa INTEGER NOT NULL);
              CREATE UNIQUE INDEX IF NOT EXISTS area_data_ativa ON reservas(area,data) WHERE ativa=1;
              CREATE TABLE IF NOT EXISTS visitantes(
                id TEXT PRIMARY KEY, apartamento TEXT NOT NULL REFERENCES apartamentos,
                nome TEXT NOT NULL, data TEXT NOT NULL, operacao TEXT UNIQUE);
              CREATE TABLE IF NOT EXISTS sessoes(
                id TEXT PRIMARY KEY, apartamento TEXT NOT NULL REFERENCES apartamentos);
              CREATE TABLE IF NOT EXISTS decisoes(
                id TEXT PRIMARY KEY, sessao TEXT NOT NULL REFERENCES sessoes,
                confirmado INTEGER NOT NULL, original_id TEXT NOT NULL,
                acao TEXT NOT NULL, argumentos TEXT NOT NULL);
              CREATE TABLE IF NOT EXISTS operacoes(id TEXT PRIMARY KEY, resultado TEXT NOT NULL);
            """)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        finally:
            db.close()

    def apartment_exists(self, apartment: str) -> bool:
        with self.connect() as db:
            return (
                db.execute(
                    "SELECT 1 FROM apartamentos WHERE numero=?", (apartment,)
                ).fetchone()
                is not None
            )

    def add_session(self, session_id: str, apartment: str) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO sessoes VALUES (?,?)", (session_id, apartment))

    def apartment(self, session_id: str) -> str | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT apartamento FROM sessoes WHERE id=?", (session_id,)
            ).fetchone()
            return row[0] if row else None

    def areas(self) -> list[dict]:
        with self.connect() as db:
            return [dict(x) for x in db.execute("SELECT * FROM areas ORDER BY id")]

    def area(self, area: str) -> dict | None:
        return next((x for x in self.areas() if x["id"] == area), None)

    def reservations(self, apartment: str) -> list[dict]:
        with self.connect() as db:
            return [
                dict(x)
                for x in db.execute(
                    "SELECT codigo,area,data FROM reservas WHERE apartamento=? AND ativa=1 ORDER BY data,codigo",
                    (apartment,),
                )
            ]

    def visitors(self, apartment: str) -> list[dict]:
        with self.connect() as db:
            return [
                dict(x)
                for x in db.execute(
                    "SELECT nome,data FROM visitantes WHERE apartamento=? ORDER BY data,nome",
                    (apartment,),
                )
            ]

    def available(self, area: str, day: str) -> bool:
        with self.connect() as db:
            return (
                db.execute(
                    "SELECT 1 FROM reservas WHERE area=? AND data=? AND ativa=1",
                    (area, day),
                ).fetchone()
                is None
            )

    def decided(self, confirmation_id: str) -> bool:
        with self.connect() as db:
            return (
                db.execute(
                    "SELECT 1 FROM decisoes WHERE id=?", (confirmation_id,)
                ).fetchone()
                is not None
            )

    def decide(
        self, confirmation_id: str, session: str, approved: bool, original: dict
    ) -> bool:
        try:
            with self.connect() as db:
                db.execute(
                    "INSERT INTO decisoes VALUES (?,?,?,?,?,?)",
                    (
                        confirmation_id,
                        session,
                        approved,
                        original["id"],
                        original["name"],
                        json.dumps(original.get("args", {}), sort_keys=True),
                    ),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def approved(
        self, session: str, call_id: str, action: str, arguments: dict
    ) -> bool:
        with self.connect() as db:
            return (
                db.execute(
                    "SELECT 1 FROM decisoes WHERE sessao=? AND original_id=? AND acao=? AND argumentos=? AND confirmado=1",
                    (session, call_id, action, json.dumps(arguments, sort_keys=True)),
                ).fetchone()
                is not None
            )

    def reserve(self, apartment: str, area: str, day: str, operation: str) -> dict:
        validate_day(day)
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            previous = db.execute(
                "SELECT resultado FROM operacoes WHERE id=?", (operation,)
            ).fetchone()
            if previous:
                return json.loads(previous[0])
            code = "RSV-" + uuid4().hex.upper()
            try:
                db.execute(
                    "INSERT INTO reservas VALUES (?,?,?,?,1)",
                    (code, apartment, area, day),
                )
                result = {
                    "status": "reservada",
                    "codigo": code,
                    "area": area,
                    "data": day,
                }
            except sqlite3.IntegrityError as exc:
                if "reservas.area, reservas.data" not in str(exc):
                    raise
                result = {"status": "indisponivel", "area": area, "data": day}
            db.execute(
                "INSERT INTO operacoes VALUES (?,?)", (operation, json.dumps(result))
            )
            return result

    def cancel(self, apartment: str, area: str, day: str) -> dict:
        with self.connect() as db:
            count = db.execute(
                "UPDATE reservas SET ativa=0 WHERE apartamento=? AND area=? AND data=? AND ativa=1",
                (apartment, area, day),
            ).rowcount
            return {
                "status": "cancelada" if count else "reserva_propria_nao_encontrada"
            }

    def authorize(self, apartment: str, name: str, day: str, operation: str) -> dict:
        validate_day(day)
        if not name.strip():
            return {"status": "nome_invalido"}
        with self.connect() as db:
            db.execute(
                "INSERT OR IGNORE INTO visitantes VALUES (?,?,?,?,?)",
                (str(uuid4()), apartment, name.strip(), day, operation),
            )
        return {"status": "autorizado", "nome": name.strip(), "data": day}
