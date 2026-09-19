import shutil
from pathlib import Path

import pytest

from aurora.config import Settings
from aurora.store import restore


@pytest.fixture
def settings(tmp_path):
    shutil.copytree(Path(__file__).parents[1] / "dados", tmp_path / "dados")
    value = Settings(tmp_path)
    restore(value)
    return value
