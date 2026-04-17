from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str = "sk-ant-REPLACE_ME"
    database_url: str = "sqlite:///./local.db"
    cors_origins: str = "http://localhost:3000"
    claude_model: str = "claude-sonnet-4-6"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
