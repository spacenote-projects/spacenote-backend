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
    telegram_bot_token: str | None = None  # Telegram Bot API token for notifications (optional)
    # Build metadata injected during Docker build via environment variables
    git_commit_hash: str = "unknown"  # Git commit hash at build time (for debugging deployments)
    git_commit_date: str = "unknown"  # Git commit date at build time (for tracking release timeline)
    build_time: str = "unknown"  # Docker image build timestamp (for identifying exact build)

    model_config = {
        "env_file": [".env"],
        "env_prefix": "SPACENOTE_",
        "extra": "ignore",
    }
