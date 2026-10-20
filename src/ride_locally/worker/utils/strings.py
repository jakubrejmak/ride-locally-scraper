import re
from typing import Any

from unidecode import unidecode


class Strings:
    @staticmethod
    def normalize(string: Any, *, strip_diacritics: bool = False) -> str:
        if strip_diacritics:
            string = Strings.strip_diacritics(string)
        return re.sub(r"\s+", " ", str(string).strip().casefold())


    @staticmethod
    def strip_diacritics(string: str) -> str:
        return unidecode(string)