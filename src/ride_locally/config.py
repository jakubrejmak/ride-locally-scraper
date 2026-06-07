from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    OPENROUTER_API_KEY: str
    DATABASE_URL: str
    ALEMBIC_DATABASE_URL: str

    SCRAPER_POLL_INTERVAL: int = 3600
    SCRAPER_WORKER_COUNT: int = 4

    PROCESSOR_POLL_INTERVAL: int = 3600
    PROCESSOR_WORKER_COUNT: int = 4

    DEBUG_OUTPUTS: bool = True
    DEBUG_OUTPUT_DIR: str = "output_files/debug"
    SCRAPER_OUTPUT_DIR: str = "output_files/scraper"
    PROCESSOR_OUTPUT_DIR: str = "output_files/processor"

    API_ADMIN_EMAIL: str = "admin@email.com"
    API_ADMIN_USERNAME: str = "admin"
    API_ADMIN_PASSWORD: str = "changeme"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    API_ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]


config = Config()
