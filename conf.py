import os
from typing import get_type_hints

from dotenv import load_dotenv

load_dotenv()


class Config:
    DATABASE_URL: str
    SRC_T_POLL_INTERVAL: int
    SCR_OUTPUT_DIR = "output_files/o_scraper"
    PCS_OUTPUT_DIR = "output_files/o_processor"
    OPENROUTER_API_KEY: str

    def __init__(self):
        for key, type_ in get_type_hints(self).items():
            setattr(self, key, type_(os.environ[key]))


config = Config()
