from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    OPENROUTER_API_KEY: str
    DATABASE_URL: str
    ALEMBIC_DATABASE_URL: str

    SCRAPER_WORKER_COUNT: int = 4
    SCRAPER_POLL_FALLBACK: int = 30

    PROCESSOR_WORKER_COUNT: int = 4
    PROCESSOR_POLL_FALLBACK: int = 30

    # worker id override (defaults to hostname:pid at startup)
    WORKER_ID: str = ""
    # how often the reaper scans for abandoned claims
    WORKER_REAPER_INTERVAL: int = 60
    # a claim held longer than this is considered abandoned
    WORKER_STALE_CLAIM_SECONDS: int = 900

    LOG_DIR: str = f"{PROJECT_ROOT}/logs"
    LOG_LVL: str = "INFO"

    DEBUG_OUTPUTS: bool = True
    DEBUG_OUTPUT_DIR: str = f"{PROJECT_ROOT}/output_files/debug"

    SCRAPER_OUTPUT_DIR: str = f"{PROJECT_ROOT}/output_files/scraper"
    PROCESSOR_OUTPUT_DIR: str = f"{PROJECT_ROOT}/output_files/processor"

    SCRAPER_SCRIPTS_DIR: str = f"{PROJECT_ROOT}/src/ride_locally/worker/scrapers/scraper_scripts"
    PREPROCESSOR_SCRIPT_DIR: str = f"{PROJECT_ROOT}/src/ride_locally/worker/preprocessor/preprocessor_scripts"

    PREPROCESSOR_PROMPTS_DIR: str = f"{PROJECT_ROOT}/src/ride_locally/worker/system_prompts/preprocessor_prompts"
    PROCESSOR_PROMPTS_DIR: str = f"{PROJECT_ROOT}/src/ride_locally/worker/system_prompts/processor_prompts"

    API_ADMIN_EMAIL: str = "admin@email.com"
    API_ADMIN_USERNAME: str = "admin"
    API_ADMIN_PASSWORD: str = "admin"
    API_HOST: str = "127.0.0.1"
    API_PORT: int = 8000
    API_RELOAD: bool = True
    API_ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    @model_validator(mode="after")
    def _ensure_log_dir(self) -> "Config":
        Path(self.LOG_DIR).mkdir(parents=True, exist_ok=True)
        return self


config = Config() # pyright: ignore[reportCallIssue]
