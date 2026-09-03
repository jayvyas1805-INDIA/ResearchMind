"""
Application configuration.

All settings are loaded from environment variables (via a .env file in
development). Nothing here should ever contain a hardcoded secret.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- General ---
    APP_NAME: str = "PaperMind"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # --- Database ---
    DATABASE_URL: str = "sqlite:///./data/papermind.db"

    # --- Storage ---
    UPLOAD_DIR: str = "./data/uploads"
    INDEX_DIR: str = "./indexes"

    # --- Upload limits ---
    MAX_UPLOAD_SIZE_MB: int = 25

    # --- Embeddings ---
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384  # must match EMBEDDING_MODEL's output dimension

    # --- Chunking ---
    CHUNK_TARGET_WORDS: int = 180
    CHUNK_MIN_WORDS: int = 40  # trailing chunks smaller than this get merged into the previous one

    # --- Retrieval ---
    DEFAULT_TOP_K: int = 5
    MIN_SIMILARITY_THRESHOLD: float = 0.2  # results below this score are dropped as not relevant

    # --- LLM provider (configurable; default = local open-source via Ollama) ---
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "llama3.1"
    OLLAMA_BASE_URL: str = "http://localhost:11434"

    # Cloud provider keys (optional, only needed if LLM_PROVIDER is switched)
    OPENAI_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor so we parse the environment only once."""
    return Settings()
