import argparse
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from .api import create_app
from .config import Settings
from .store import restore


def main():
    parser = argparse.ArgumentParser(description="Residencial Aurora")
    parser.add_argument("command", choices=["restore", "start"])
    args = parser.parse_args()
    settings = Settings(Path.cwd())
    if args.command == "restore":
        restore(settings)
        print(
            "Restaurados exclusivamente .runtime/aurora/domain.sqlite3 e adk.sqlite3. Sessões removidas."
        )
        return
    load_dotenv(settings.root / ".env")
    uvicorn.run(create_app(settings), host="127.0.0.1", port=8000)
