import os
from dotenv import load_dotenv
from typing import get_type_hints

load_dotenv()

class Config:
    DATABASE_URL: str
    SRC_T_POLL_INTERVAL: int

    def __init__(self):
        for key, type_ in get_type_hints(self).items():
            setattr(self, key, type_(os.environ[key]))

config = Config()
