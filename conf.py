import os
from typing import get_type_hints

from dotenv import load_dotenv

load_dotenv()


class Config:
    OPENROUTER_API_KEY: str

    DATABASE_URL: str

    SCRAPER_POLL_INTERVAL: int = 3600  # in seconds
    SCRAPER_WORKER_COUNT: int = 4

    PROCESSOR_POLL_INTERVAL: int = 3600  # in seconds
    PROCESSOR_WORKER_COUNT: int = 4

    DEBUG_OUTPUTS: bool = True
    DEBUG_OUTPUT_DIR: str = "output_files/debug"
    SCRAPER_OUTPUT_DIR: str = "output_files/scraper"
    PROCESSOR_OUTPUT_DIR: str = "output_files/processor"

    def __init__(self):
        for key, type_ in get_type_hints(self).items():
            setattr(self, key, type_(os.environ[key]))


config = Config()
