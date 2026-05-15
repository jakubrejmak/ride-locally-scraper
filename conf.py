import os
from dataclasses import MISSING, dataclass, fields
from typing import Any, Self, get_type_hints

from dotenv import load_dotenv

load_dotenv()


def _parse(typ: type[Any], raw: str) -> Any:
    if typ is bool:
        return raw.strip().lower() in ("1", "true", "yes", "on")
    return typ(raw)


@dataclass
class Config:
    OPENROUTER_API_KEY: str
    DATABASE_URL: str
    ALEMBIC_DATABASE_URL: str

    SCRAPER_POLL_INTERVAL: int = 3600  # seconds
    SCRAPER_WORKER_COUNT: int = 4

    PROCESSOR_POLL_INTERVAL: int = 3600  # seconds
    PROCESSOR_WORKER_COUNT: int = 4

    DEBUG_OUTPUTS: bool = True
    DEBUG_OUTPUT_DIR: str = "output_files/debug"
    SCRAPER_OUTPUT_DIR: str = "output_files/scraper"
    PROCESSOR_OUTPUT_DIR: str = "output_files/processor"

    @classmethod
    def from_env(cls) -> Self:
        values: dict[str, Any] = {}
        type_hints = get_type_hints(cls)
        for f in fields(cls):
            raw = os.environ.get(f.name)
            typ = type_hints.get(f.name)
            if raw is not None:
                if isinstance(typ, type):
                    values[f.name] = _parse(typ, raw)
                else:
                    values[f.name] = raw
            elif f.default is not MISSING:
                values[f.name] = f.default
            elif f.default_factory is not MISSING:
                values[f.name] = f.default_factory()
            else:
                raise RuntimeError(
                    f"Missing required environment variable {f.name!r}"
                ) from None
        return cls(**values)


config = Config.from_env()
