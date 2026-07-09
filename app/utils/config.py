"""
AgroSight – Centralised application configuration.
All values are loaded from environment variables (via .env or secrets backend).

Security:
  - Use .env.example as template
  - Never commit .env to git (.gitignore enforces this)
  - For production, use secrets backend:
    - SECRETS_BACKEND=aws   (AWS Secrets Manager)
    - SECRETS_BACKEND=vault (HashiCorp Vault)
    - SECRETS_BACKEND=azure (Azure Key Vault)
    - SECRETS_BACKEND=env   (Default: environment variables)
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    app_title: str = "AgroSight RAG API"
    app_version: str = "1.0.0"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    request_timeout: int = 30
    max_agent_iterations: int = 6

    # ── Secrets Backend ────────────────────────────────────────────────────
    # Options: "env", "aws", "vault", "azure"
    secrets_backend: str = "env"

    # ── LLM (Mistral API) ─────────────────────────────────────────────────
    mistral_api_key: str = ""
    mistral_model: str = "mistral-large-latest"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 4096

    # ── Qdrant ────────────────────────────────────────────────────────────
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "agricultural_knowledge_v8"

    # ── Embedding ─────────────────────────────────────────────────────────
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024

    # ── Retrieval ─────────────────────────────────────────────────────────
    retrieval_top_k: int = 8
    retrieval_score_threshold: float = 0.18
    default_chunk_tokens: int = 512
    default_overlap_tokens: int = 64

    # ── Redis ─────────────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    session_ttl_seconds: int = 86_400
    max_history_turns: int = 5

    # ── Weather ───────────────────────────────────────────────────────────
    openweather_api_key: str = ""
    openweather_base_url: str = "https://api.openweathermap.org/data/2.5"

    # ── Government data ───────────────────────────────────────────────────
    data_gov_api_key_1: str = ""
    data_gov_base_url: str = "https://api.data.gov.in"
    data_gov_mandi_resource_id: str = "9ef84268-d588-465a-a308-a864a43d0070"
    data_gov_variety_resource_id: str = "35985678-0d79-46b4-9ed6-6f13308a1d24"

    agmarknet_api_key: str = ""
    agmarknet_base_url: str = "https://agmarknet.gov.in/api"

    usda_nass_api_key: str = ""
    usda_nass_base_url: str = "https://quickstats.nass.usda.gov/api"

    fao_faostat_base_url: str = "https://fenixservices.fao.org/faostat/api/v1"
    isric_base_url: str = "https://rest.isric.org/soilgrids/v2.0"

    # ── Kaggle ────────────────────────────────────────────────────────────
    kaggle_username: str = ""
    kaggle_key: str = ""

    # ── Data paths ────────────────────────────────────────────────────────
    data_root: str = "./data/raw"
    books_dir: str = "./data/books"
    chunks_output_dir: str = "./chunks_output"

    # ── Ingestion ─────────────────────────────────────────────────────────
    max_retries: int = 3
    retry_backoff: int = 2
    batch_size: int = 100

    @field_validator("log_level", mode="before")
    @classmethod
    def normalise_log_level(cls, v: str) -> str:
        return v.upper()
    
    def validate_secrets(self) -> bool:
        """
        Validate that all required secrets are set.
        Called during application startup.
        """
        required = {
            "mistral_api_key": self.mistral_api_key,
            "qdrant_url": self.qdrant_url,
            "qdrant_api_key": self.qdrant_api_key,
        }
        
        missing = [k for k, v in required.items() if not v]
        if missing:
            raise ValueError(
                f"Missing required configuration: {', '.join(missing)}. "
                f"Set them in .env file or via environment variables."
            )
        return True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached singleton Settings instance with validation."""
    settings = Settings()
    settings.validate_secrets()
    return settings
