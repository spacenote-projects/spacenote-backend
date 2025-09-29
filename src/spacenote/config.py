from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str
    host: str
    port: int
    debug: bool
    session_secret_key: str
    cors_origins: list[str] = []
    frontend_url: str  # URL of the frontend application, e.g. https://spacenote.app

    model_config = {
        "env_file": [".env"],
        "env_prefix": "SPACENOTE_",
        "extra": "ignore",
    }
