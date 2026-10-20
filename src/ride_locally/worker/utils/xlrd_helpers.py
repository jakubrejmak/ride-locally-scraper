import xlrd


class XlrdHelper:
    @staticmethod
    def cell_as_str(sheet, row: int, col: int) -> str:
        """xlrd returns float for numbers, bool for booleans, etc. - normalize to str."""
        cell = sheet.cell(row, col)
        if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
            return ""
        if cell.ctype == xlrd.XL_CELL_NUMBER:
            value = cell.value
            if value == int(value):
                return str(int(value))
            return str(value)
        return str(cell.value).strip()

    @staticmethod
    def get_row_value_list(sheet, row_no) -> list[str]:
        return [XlrdHelper.cell_as_str(sheet, row_no, c) for c in
                range(sheet.ncols)]

    @staticmethod
    def get_rows(sheet) -> list[list[str]]:
        return [XlrdHelper.get_row_value_list(sheet, r) for r in range(sheet.nrows)]

    @staticmethod
    def get_hyperlink(sheet, row: int, col: int) -> str | None:
        """hyperlink_map is only filled when the book is opened with formatting_info=True."""
        hl = sheet.hyperlink_map.get((row, col))
        return hl.url_or_path if hl else None
