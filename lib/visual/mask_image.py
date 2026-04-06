import io

from PIL import Image, ImageDraw

from models.preprocessors import Region
from models.visual import Square, Direction


def region_to_square(region: Region) -> Square:
    """Convert a Region (with top/left/bottom/right) to a Square (with p1/p2 points)."""
    return Square(
        p1={"x": float(region.left), "y": float(region.top)},
        p2={"x": float(region.right), "y": float(region.bottom)},
    )


def cut_jpeg_img(image_bytes: bytes, square: Square) -> bytes:
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


def compose_from_squares(image_bytes: bytes, squares: list[Square]) -> bytes:
    """
    Compose a new image by cutting each square from the source and pasting onto
    a white canvas with minimal dimensions, preserving relative positions.
    """
    if not squares:
        raise ValueError("At least one square must be provided")

    min_x = int(min(s["p1"]["x"] for s in squares))
    min_y = int(min(s["p1"]["y"] for s in squares))
    max_x = int(max(s["p2"]["x"] for s in squares))
    max_y = int(max(s["p2"]["y"] for s in squares))

    canvas_width = max_x - min_x
    canvas_height = max_y - min_y

    canvas = Image.new("RGB", (canvas_width, canvas_height), "white")

    for square in squares:
        cut_bytes = cut_jpeg_img(image_bytes, square)
        cut_img = Image.open(io.BytesIO(cut_bytes))
        x = int(square["p1"]["x"]) - min_x
        y = int(square["p1"]["y"]) - min_y
        canvas.paste(cut_img, (x, y))

    output = io.BytesIO()
    canvas.save(output, format="JPEG", quality=100)
    return output.getvalue()
