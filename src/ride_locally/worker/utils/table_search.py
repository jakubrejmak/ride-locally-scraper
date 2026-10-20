from collections.abc import Iterable, Mapping

from ride_locally.worker.utils.strings import Strings


class TableSearch:
    """Lookups over rows of cell strings. Ignore case, whitespace, and diacritics."""

    @staticmethod
    def find_row(
        sheets: list[list[list[str]]], values: Iterable[str]
    ) -> tuple[int, int] | tuple[None, None]:
        """(sheet index, row index) of the first row containing all values."""
        needles = [Strings.normalize(v, strip_diacritics=True) for v in values]

        for i, rows in enumerate(sheets):
            for r, row in enumerate(rows):
                row_text = Strings.normalize(" ".join(row), strip_diacritics=True)
                if all(n in row_text for n in needles):
                    return i, r

        return None, None

    @staticmethod
    def find_columns(row: list[str], values: Mapping[str, str]) -> dict[str, int]:
        """Maps each key to the first cell containing its value. Keys whose value isn't
        found are left out."""
        cells = [Strings.normalize(cell, strip_diacritics=True) for cell in row]

        found: dict[str, int] = {}
        # longest value first, so one that is a substring of another can't claim the other's column
        for key, value in sorted(values.items(), key=lambda kv: len(kv[1]), reverse=True):
            needle = Strings.normalize(value, strip_diacritics=True)
            for c, cell in enumerate(cells):
                if c not in found.values() and needle in cell:
                    found[key] = c
                    break

        return found
