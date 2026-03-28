from models.visual import Square, Direction


async def mask_image_half(
    image_bytes: bytes, split_percentage: float, direction: Direction
) -> bytes | None:
    pass


async def mask_image_sq(image_bytes: bytes, square: Square) -> bytes | None:
    pass
