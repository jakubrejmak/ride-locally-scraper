import io

import numpy as np
from deskew import determine_skew
from PIL import Image
from skimage.transform import rotate


def deskew_image(image_bytes: bytes) -> bytes:
    """Deskew an image based on detected text angle and return corrected JPEG bytes."""
    image = np.array(Image.open(io.BytesIO(image_bytes)))
    angle = determine_skew(image)
    rotated = rotate(image, angle, resize=True) * 255

    output = io.BytesIO()
    Image.fromarray(rotated.astype(np.uint8)).save(output, format="JPEG", quality=100)
    return output.getvalue()
