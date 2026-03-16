from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Smart Legal Document Manager"
    database_url: str = "sqlite:///./smart_legal_manager.db"
    similarity_threshold: float = 0.95
    max_content_length: int = 1_000_000
    page_size_default: int = 10
    page_size_max: int = 100

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
