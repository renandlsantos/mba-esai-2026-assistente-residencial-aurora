"""Processo HTTP usado somente no teste offline de reinício real."""

import sys
from pathlib import Path

import uvicorn

from aurora.api import create_app
from aurora.config import Settings
from tests.fake_model import ScriptedModel

if __name__ == "__main__":
    uvicorn.run(
        create_app(Settings(Path(sys.argv[1])), model=ScriptedModel()),
        host="127.0.0.1",
        port=int(sys.argv[2]),
        log_level="error",
    )
