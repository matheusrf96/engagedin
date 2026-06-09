from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    linkedin_client_id: str = ""
    linkedin_client_secret: str = ""
    linkedin_access_token: str = ""
    linkedin_user_urn: str = ""

    llm_provider: str = "deepseek"
    llm_api_key: str = ""
    llm_model: str = "deepseek-chat"

    news_source: str = "hackernews"
    news_api_key: str = ""

    rules_path: str = ""


settings = Settings()
