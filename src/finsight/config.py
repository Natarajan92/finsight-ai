"""Explicit application configuration; no import-time environment loading."""

from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FINSIGHT_", env_file=".env", extra="ignore")

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    source_pdf_dir: Path = Path("source-data/pdfs")
    artifact_dir: Path = Path("data")
    api_key: SecretStr | None = None
    nebius_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    manifest_path: Path = Path("data/manifests/financebench-selected.json")
    page_cache_root: Path = Path("data/cache/pages")
    tokenizer_dir: Path = Path("data/cache/tokenizer/qwen3-embedding-8b")
    embedding_cache_root: Path = Path("data/cache/embeddings")
    index_root: Path = Path("data/indexes")
    rates_path: Path = Path("data/cache/budget/rates.json")
    ledger_path: Path = Path("data/cache/budget/testing.sqlite3")
    trace_root: Path = Path("results/traces")
    index_job_timeout_s: int = Field(default=14400, ge=60, le=14400)
