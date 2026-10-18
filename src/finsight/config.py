"""Explicit application configuration; no import-time environment loading."""

from pathlib import Path
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FINSIGHT_", env_file=".env", extra="ignore")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    source_pdf_dir: Path = Path("source-data/pdfs")
    artifact_dir: Path = Path("data")
    api_key: SecretStr | None = None
    nebius_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
