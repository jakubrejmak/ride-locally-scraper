from models.files import FileData, ScrRunResult

async def run(input: ScrRunResult, **kwargs) -> ScrRunResult | None:
    """this internally calls deskew_image from lib.visual. WARNING: because of its
    straight edges table deskew can produce a table that is rotated either 0deg or 90deg.
    need some text recognition first to hint a proper orientation
    """
    pass
