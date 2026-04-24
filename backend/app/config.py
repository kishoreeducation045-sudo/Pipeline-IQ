# app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    anthropic_api_key: str
    github_token: str = ""
    github_webhook_secret: str = ""
    gitlab_webhook_secret: str = ""
    claude_model: str = "claude-sonnet-4-5"
    sqlite_path: str = "/data/pipelineiq.db"
    chroma_path: str = "/data/chroma"
    cors_origins: list[str] = ["http://localhost:5173"]
    log_level: str = "INFO"
    minutes_saved_per_failure: int = 120
    dev_hourly_usd: int = 100
    llm_cost_per_rca_usd: float = 0.04

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
