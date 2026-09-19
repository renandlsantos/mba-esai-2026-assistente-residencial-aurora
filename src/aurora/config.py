from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    root: Path

    @property
    def runtime(self) -> Path:
        return self.root / ".runtime" / "aurora"

    @property
    def domain_db(self) -> Path:
        return self.runtime / "domain.sqlite3"

    @property
    def adk_db(self) -> Path:
        return self.runtime / "adk.sqlite3"

    @property
    def data(self) -> Path:
        return self.root / "dados"
