from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://engagedin:engagedin@localhost:5432/engagedin"
    )
    api_host: str = "127.0.0.1"
    api_port: int = 8000


api_settings = ApiSettings()
