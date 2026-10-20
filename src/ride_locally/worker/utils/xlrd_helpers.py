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
    def find_row(book: xlrd.Book, values: tuple[str, ...]):
        for i, sheet in enumerate(book.sheets()):
            for r in range(sheet.nrows):
                row_text = " ".join(
                    XlrdHelper.cell_as_str(sheet, r, c) for c in range(sheet.ncols)
                )
                if all(n in row_text for n in values):
                    return i, r

        return None, None

    @staticmethod
    def get_row_value_list(sheet, row_no) -> list[str]:
        return [XlrdHelper.cell_as_str(sheet, row_no, c) for c in range(sheet.ncols)]
