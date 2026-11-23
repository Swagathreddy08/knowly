from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    jwt_secret: str = "change-this-to-a-long-random-secret-at-least-32-characters"
    jwt_expiry_minutes: int = 60
    database_url: str = "sqlite:///./data/knowly.db"
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    tika_url: str = "http://localhost:9998"
    pinecone_api_key: str = ""
    pinecone_index: str = ""
    elasticsearch_url: str = "http://localhost:9200"
    cohere_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    cors_origins: str = "http://localhost:3000"
    max_upload_size_mb: int = 25
    upload_dir: Path = Path("./uploads")

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @field_validator("jwt_secret")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must contain at least 32 characters")
        return value


settings = Settings()
