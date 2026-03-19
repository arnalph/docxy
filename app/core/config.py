from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Docxy"
    API_V1_STR: str = "/api/v1"

    # POSTGRES / SQLITE
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "pdf_extractor"
    DATABASE_URL: Optional[str] = "sqlite+aiosqlite:///./docxy.db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: Optional[str], info):
        if isinstance(v, str) and v:
            return v
        # Build from postgres components
        return f"postgresql+asyncpg://{info.data.get('POSTGRES_USER')}:{info.data.get('POSTGRES_PASSWORD')}@{info.data.get('POSTGRES_SERVER')}/{info.data.get('POSTGRES_DB')}"

    # REDIS
    USE_REDIS: bool = False
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    REDIS_URL: Optional[str] = None

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: Optional[str], info):
        if isinstance(v, str) and v:
            return v
        if info.data.get("USE_REDIS"):
            password_part = f":{info.data.get('REDIS_PASSWORD')}@" if info.data.get('REDIS_PASSWORD') else ""
            return f"redis://{password_part}{info.data.get('REDIS_HOST')}:{info.data.get('REDIS_PORT')}"
        return None

    # S3 / Minio / LOCAL
    STORAGE_TYPE: str = "local"  # "s3" or "local"
    UPLOAD_DIR: str = "uploads"
    S3_ENDPOINT: str = "http://minio:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET: str = "documents"

    # LiteLLM
    LITELLM_BASE_URL: str = "http://llm:11434"
    LITELLM_API_KEY: str = "ollama"
    LITELLM_MODEL_NAME: str = "ollama/llama3"

    # Rate Limiting
    INBOUND_RATE_LIMIT: str = "100/hour"

    # Admin Auth
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin"
    SECRET_KEY: str = "secret-key-change-me-in-production"

    # Poppler path for pdf2image (Windows)
    POPPLER_PATH: Optional[str] = None

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()