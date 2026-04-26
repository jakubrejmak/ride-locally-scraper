import os
from typing import get_type_hints

from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL: str
    SRC_T_POLL_INTERVAL: int
    OPENROUTER_API_KEY: str
    DEBUG_PROCESSOR_OUTPUT: bool = True
    DEBUG_OUTPUT_DIR: str = "output_files/debug"
    SCRAPER_OUTPUT_DIR: str = "output_files/scraper"
    PROCESSOR_OUTPUT_DIR: str = "output_files/processor"

    def __init__(self):
        for key, type_ in get_type_hints(self).items():
            setattr(self, key, type_(os.environ[key]))


config = Config()
