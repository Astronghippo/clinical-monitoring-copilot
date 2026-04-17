from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    anthropic_api_key: str = "sk-ant-REPLACE_ME"
    database_url: str = "sqlite:///./local.db"
    # Comma-separated list of allowed origins. "*" permits any origin — fine for
    # a public prototype. Tighten for production (e.g. "https://cmc.yoursite.com").
    cors_origins: str = "*"
    claude_model: str = "claude-sonnet-4-6"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
