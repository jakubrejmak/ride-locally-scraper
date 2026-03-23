import mimetypes
import os
import uuid
from pathlib import Path

import magic

from models.types import PcsRunResult, ScrTargetResult


def _split_mime(mimetype: str) -> str:
    return mimetype.split("/")[1]


def mime_from_bytes(data: bytes) -> tuple[str, str]:
    full_mime = magic.from_buffer(data, mime=True)
    return full_mime, _split_mime(full_mime)


def mime_from_file(path: str) -> tuple[str, str]:
    if not os.path.isfile(path):
        raise ValueError(f"Expected a valid file, got: {path}")
    full_mime = magic.from_file(path, mime=True)
    return full_mime, _split_mime(full_mime)


def mime_from_path(path: str) -> tuple[str | None, str | None]:
    full_mime = mimetypes.guess_type(path)[0]
    ext = os.path.splitext(path)[1].lstrip(".") or None
    return full_mime, ext


def mime_from_url(url: str) -> tuple[str | None, str | None]:
    path = url.split("?")[0]
    full_mime = mimetypes.guess_type(path)[0]
    ext = os.path.splitext(path)[1].lstrip(".") or None
    return full_mime, ext


def save_result(result: ScrTargetResult | PcsRunResult) -> str | None:
    SCR_OUTPUT_DIR = Path(__file__).parent.parent / "output_files" / "o_scraper"
    PCS_OUTPUT_DIR = Path(__file__).parent.parent / "output_files" / "o_processor"
    output_dir = (
        SCR_OUTPUT_DIR if isinstance(result, ScrTargetResult) else PCS_OUTPUT_DIR
    )

    output_dir.mkdir(exist_ok=True)
    if result is None or len(result.data) < 1:
        return None
    elif len(result.data) == 1:
        file = output_dir / f"{uuid.uuid4().hex}.{result.data[0].ext}"
        with open(file, "wb") as f:
            f.write(result.data[0].bytes)
        return str(file)
    else:
        nest_dir = output_dir / f"{uuid.uuid4().hex}"
        Path(nest_dir).mkdir(parents=True, exist_ok=True)
        for d in result.data:
            file = nest_dir / f"{uuid.uuid4().hex}.{d.ext}"
            with open(file, "wb") as f:
                f.write(d.bytes)
        return str(nest_dir)
