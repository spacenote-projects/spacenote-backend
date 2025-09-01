from pydantic_settings import BaseSettings


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    database_url: str
    host: str
    port: int
    debug: bool
    session_secret_key: str
    cors_origins: list[str] = []

    model_config = {
        "env_file": [".env"],
        "env_prefix": "SPACENOTE_",
        "extra": "ignore",
    }
