from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "SmartLoan AI"
    api_v1_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./smartloan_ai.db"
    secret_key: str = "change-this-secret-key-later"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
