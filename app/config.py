from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4-turbo-preview"
    database_path: str = "./deals.db"

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
