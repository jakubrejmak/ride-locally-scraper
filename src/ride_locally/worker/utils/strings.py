import re
from typing import Any

from unidecode import unidecode


class Strings:
    @staticmethod
    def normalize(string: Any) -> str:
        return re.sub(r"\s+", " ", str(string).strip().casefold())


    @staticmethod
    def strip_diacritics(string: str) -> str:
        return unidecode(string)