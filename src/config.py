"""
Application configuration via environment variables with pydantic-settings.

All settings are loaded from environment variables (.env file optional).
Secrets and API keys are NEVER hardcoded.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "Cost Report AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Server ───────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1

    # ── LLM Provider (LiteLLM) ───────────────────────────────────
    LLM_PROVIDER: str = "openai"  # openai, azure, anthropic, groq, etc.
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_API_KEY: str = ""  # Set via env var: COST_REPORT_AI__LLM_API_KEY
    LLM_TEMPERATURE: float = 0.0  # Deterministic output for auditability
    LLM_MAX_TOKENS: int = 4096
    LLM_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ── Classification ──────────────────────────────────────────
    CLASSIFIER_HIGH_CONFIDENCE_THRESHOLD: float = 0.90
    CLASSIFIER_MEDIUM_CONFIDENCE_THRESHOLD: float = 0.70
    CLASSIFIER_DEFAULT_FALLBACK_COST_CENTER: str = "04"
    CLASSIFIER_FEW_SHOT_EXAMPLES: int = 5

    # ── Data Paths ──────────────────────────────────────────────
    DATA_DIR: Path = Path("data")
    SAMPLES_DIR: Path = Path("data/samples")
    OUTPUT_DIR: Path = Path("data/output")
    FACILITY_REGISTRY_DIR: Path = Path("src/facilities")

    # ── Parser ──────────────────────────────────────────────────
    PARSER_MAX_FILE_SIZE_MB: int = 50
    PARSER_CHUNK_SIZE_ROWS: int = 10000

    # ── Audit / Lineage ─────────────────────────────────────────
    LINEAGE_ENABLED: bool = True
    LINEAGE_LOG_DIR: Path = Path("data/lineage")

    # ── Security ────────────────────────────────────────────────
    API_KEY: str = ""  # Optional: API key for endpoint protection
    CORS_ORIGINS: list[str] = ["*"]


settings = Settings()

# Ensure output directories exist
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
if settings.LINEAGE_ENABLED:
    settings.LINEAGE_LOG_DIR.mkdir(parents=True, exist_ok=True)
