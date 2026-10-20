from typing import Any


class OpenpyxlHelper:
    @staticmethod
    def cell_as_str(value: Any) -> str:
        """openpyxl returns int/float for numbers, datetime for dates, etc. - normalize to str."""
        if value is None:
            return ""
        if isinstance(value, float) and value == int(value):
            return str(int(value))
        return str(value).strip()

    @staticmethod
    def get_rows(sheet) -> list[list[str]]:
        return [
            [OpenpyxlHelper.cell_as_str(v) for v in row]
            for row in sheet.iter_rows(values_only=True)
        ]

    @staticmethod
    def get_hyperlink(sheet, row: int, col: int) -> str | None:
        """Hyperlinks aren't loaded when the workbook is opened with read_only=True."""
        hl = sheet.cell(row=row, column=col).hyperlink
        return hl.target if hl else None
