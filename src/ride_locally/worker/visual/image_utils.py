import io

from PIL import Image, ImageDraw

from ride_locally.models.visual import Direction, Square
from ride_locally.worker.llm.llm_structured_outputs import Region


def region_to_square(region: Region) -> Square:
    """Convert a Region (with top/left/bottom/right) to a Square (with p1/p2 points)."""
    return Square(
        p1={"x": float(region.left), "y": float(region.top)},
        p2={"x": float(region.right), "y": float(region.bottom)},
    )


def crop_image_to_square(image_bytes: bytes, square: Square) -> bytes:
    """Cut a region from an image and return the cropped JPEG bytes."""
    img = Image.open(io.BytesIO(image_bytes))
    x1, y1 = int(square["p1"]["x"]), int(square["p1"]["y"])
    x2, y2 = int(square["p2"]["x"]), int(square["p2"]["y"])
    cropped = img.crop((x1, y1, x2, y2))
    output = io.BytesIO()
    cropped.save(output, format="JPEG", quality=100)
    return output.getvalue()


def mask_jpeg_img(image_bytes: bytes, square: Square) -> bytes:
    """Mask a region in an image with a white rectangle and return the modified JPEG bytes."""
    img = Image.open(io.BytesIO(image_bytes))
    draw = ImageDraw.Draw(img)

    x1, y1 = square["p1"]["x"], square["p1"]["y"]
    x2, y2 = square["p2"]["x"], square["p2"]["y"]

    draw.rectangle([x1, y1, x2, y2], fill="white")

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=100)
    return output.getvalue()


def _stack_images(
    image_bytes: list[bytes],
    direction: Direction,
) -> bytes:
    if len(image_bytes) == 1:
        return image_bytes[0]

    images = []
    max_size = 0
    total_size = 0

    for bytes in image_bytes:
        image = Image.open(io.BytesIO(bytes))
        if direction == "horizontal":
            max_size = max(max_size, image.height)
            total_size += image.width
            images.append(image)
        else:
            max_size = max(max_size, image.width)
            total_size += image.height
            images.append(image)

    # Create canvas and stack image_bytes
    canvas_size = (
        (total_size, max_size) if direction == "horizontal" else (max_size, total_size)
    )
    canvas = Image.new("RGB", canvas_size, "white")

    offset = 0
    for img in images:
        if direction == "horizontal":
            if img.height < max_size:
                img = img.resize((img.width, max_size))
            canvas.paste(img, (offset, 0))
            offset += img.width
        else:
            if img.width < max_size:
                img = img.resize((max_size, img.height))
            canvas.paste(img, (0, offset))
            offset += img.height

    output = io.BytesIO()
    canvas.save(output, format="JPEG", quality=100)
    return output.getvalue()


def stack_images_vertical(images: list[bytes]) -> bytes:
    """Stack images vertically"""
    return _stack_images(images, "vertical")


def stack_images_horizontal(images: list[bytes]) -> bytes:
    """Stack images horizontally"""
    return _stack_images(images, "horizontal")
