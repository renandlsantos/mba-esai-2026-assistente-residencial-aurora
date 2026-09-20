import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier

import pytest

from aurora.config import Settings
from aurora.store import Store, restore


def test_sql_unique_under_real_thread_contention(settings):
    barrier = Barrier(2)
    store = Store(settings)

    def book(apartment):
        barrier.wait()
        return store.reserve(apartment, "quadra", "2030-07-01", apartment)

    with ThreadPoolExecutor(2) as pool:
        results = list(pool.map(book, ["101", "201"]))
    assert sorted(x["status"] for x in results) == ["indisponivel", "reservada"]


def test_codes_and_idempotency(settings):
    store = Store(settings)
    store.cancel("101", "quadra", "2030-03-09")
    first = store.reserve("101", "quadra", "2030-03-09", "op1")
    assert first["codigo"] != "RSV-1377"
    assert store.reserve("101", "quadra", "2030-03-09", "op1") == first
    store.cancel("101", "quadra", "2030-03-09")
    second = store.reserve("101", "quadra", "2030-03-09", "op2")
    assert second["codigo"] not in {"RSV-1377", first["codigo"]}


def test_compact_date_cannot_bypass_exclusivity(settings):
    store = Store(settings)
    store.reserve("101", "quadra", "2030-06-01", "canonical")
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        store.reserve("201", "quadra", "20300601", "compact")


def test_restore_refuses_foreign_directory_and_symlinks(settings, tmp_path):
    foreign = Settings(tmp_path / "foreign")
    foreign.runtime.mkdir(parents=True)
    db = foreign.domain_db
    db.write_text("foreign data")
    with pytest.raises(ValueError, match="sem marcador"):
        Store(foreign)
    assert db.read_text() == "foreign data"
    target = tmp_path / "outside.db"
    target.write_text("not owned")
    settings.adk_db.symlink_to(target)
    with pytest.raises(ValueError, match="link"):
        restore(settings)
    assert target.read_text() == "not owned"


def test_restore_only_own_files_and_frozen_data(settings):
    unrelated = settings.root / "unrelated.db"
    unrelated.write_text("keep")
    source_hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in settings.data.iterdir()
    }
    store = Store(settings)
    store.reserve("101", "quadra", "2030-04-30", "once")
    store.add_session("session", "101")
    restore(settings)
    restored = Store(settings)
    assert restored.apartment("session") is None
    assert len(restored.reservations("101")) == 1
    assert unrelated.read_text() == "keep"
    assert source_hashes == {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in settings.data.iterdir()
    }


def test_starter_integrity():
    root = Path(__file__).parents[1]
    expected = json.loads((root / "docs/upstream-integrity.json").read_text())
    assert {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in expected
    } == expected
