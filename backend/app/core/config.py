"""Centralised application configuration.

Every environment-driven setting lives here. No other module reads
`os.environ` directly — they call `get_settings()` instead, so there is one
place to look when you want to know what is configurable.
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---------------------------------------------------------
    app_name: str = "AI Recruitment MVP"
    app_version: str = "1.0.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    host: str = "0.0.0.0"
    port: int = 8000

    # --- CORS ----------------------------------------------------------------
    # The Next.js dev server runs on 3000; 3001 is the usual fallback port when
    # 3000 is already taken.
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:3001"]

    # --- Database ------------------------------------------------------------
    # PostgreSQL is the intended database (see docker-compose.yml). SQLite is
    # accepted so the project can be run and demoed with nothing installed.
    database_url: str = "postgresql+psycopg://recruit:recruit@localhost:5432/recruitment"

    # --- JWT -----------------------------------------------------------------
    jwt_secret_key: str = "change-this-to-a-random-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 720

    # --- LLM -----------------------------------------------------------------
    # Provider is chosen once here and used by all three agents. "fallback"
    # forces the deterministic rule-based agents, which need no API key at all —
    # useful for offline demos and for the test suite.
    llm_provider: str = "groq"  # groq | openai | gemini | ollama | fallback
    llm_model: str = "openai/gpt-oss-120b"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 2048
    llm_timeout_seconds: int = 60

    groq_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # --- RAG -----------------------------------------------------------------
    # "local" uses the MiniLM model bundled with ChromaDB: no API key, no
    # network call, and small enough to embed a resume in well under a second.
    embedding_provider: str = "local"  # local | openai | gemini | ollama
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 800
    chunk_overlap: int = 120
    retrieval_top_k: int = 4

    # --- Storage -------------------------------------------------------------
    upload_dir: str = "./data/uploads"
    chroma_persist_dir: str = "./data/chroma"
    max_upload_size_mb: int = 10

    # --- Logging -------------------------------------------------------------
    log_level: str = "INFO"

    @property
    def upload_path(self) -> Path:
        return _resolve(self.upload_dir)

    @property
    def chroma_path(self) -> Path:
        return _resolve(self.chroma_persist_dir)

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


def _resolve(raw: str) -> Path:
    """Resolve a configured path relative to the backend root, not the CWD.

    Without this, starting uvicorn from the repository root instead of from
    `backend/` would silently create a second, empty data directory.
    """
    path = Path(raw)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
