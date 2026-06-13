from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # OpenAI
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    openai_vision_model: str = "gpt-4o-mini"

    # Auth
    secret_key: str = "change-me"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7

    # Database
    database_url: str = "sqlite:///./data/app.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # CORS
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    # RAG
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_results: int = 5
    min_relevance_score: float = 0.0

    # Rate limiting
    rate_limit_per_minute: int = 30

    # Cost tracking
    cost_tracking_enabled: bool = True

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    storage_dir: Path = base_dir / "storage"
    data_dir: Path = base_dir / "data"
    chroma_dir: Path = data_dir / "chroma"

    @property
    def user_storage_root(self) -> Path:
        return self.storage_dir / "users"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
