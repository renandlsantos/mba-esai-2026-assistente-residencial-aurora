"""Explicit model selection; Gemini remains the academic/default provider."""

import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values


class ModelConfigurationError(RuntimeError):
    pass


def configured_model():
    provider = os.getenv("AURORA_MODEL_PROVIDER") or "gemini"
    if provider == "gemini":
        model = os.getenv("GEMINI_MODEL")
        if not model or not os.getenv("GOOGLE_API_KEY"):
            raise ModelConfigurationError(
                "Configure GOOGLE_API_KEY e GEMINI_MODEL para conversar."
            )
        return model
    if provider != "spark":
        raise ModelConfigurationError("AURORA_MODEL_PROVIDER deve ser gemini ou spark.")

    from .spark import SparkModel

    path = Path(
        os.getenv("SPARK_ENV_FILE") or "~/.config/spark/spark-api.env"
    ).expanduser()
    values = dotenv_values(path, interpolate=False) if path.is_file() else {}
    base_url = os.getenv("SPARK_BASE_URL") or values.get("SPARK_BASE_URL")
    key = os.getenv("SPARK_API_KEY") or values.get("SPARK_API_KEY")
    if not base_url or not key:
        raise ModelConfigurationError(
            "Configure SPARK_BASE_URL e SPARK_API_KEY para Spark."
        )
    parsed = urlsplit(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
    ):
        raise ModelConfigurationError(
            "SPARK_BASE_URL deve ser uma URL HTTP(S) sem credenciais ou query."
        )
    return SparkModel(base_url=base_url.rstrip("/"), api_key=key)
