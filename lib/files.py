import mimetypes
import os
import uuid
from pathlib import Path
from typing import TypeVar

import magic

from models.types import FileData, ProcessResult, ScrRunResult

TResult = TypeVar("TResult", ScrRunResult, ProcessResult)


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


def save_file_data(data: FileData, directory: str) -> str | None:
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    file = d / f"{uuid.uuid4().hex}.{data.ext}"
    with open(file, "wb") as f:
        f.write(data.bytes)
    return str(file)


def save_result(result: ProcessResult | ScrRunResult, directory: str) -> str | None:
    if result is None or len(result.data) < 1:
        return None
    elif len(result.data) == 1:
        return save_file_data(result.data[0], directory)
    else:
        nest_dir = Path(directory) / f"{uuid.uuid4().hex}"
        nest_dir.mkdir(parents=True, exist_ok=True)
        for d in result.data:
            save_file_data(d, str(nest_dir))
        return str(nest_dir)


def read_file_data(filepath: str) -> FileData | None:
    if not os.path.isfile(filepath):
        return None
    with open(filepath, "rb") as f:
        data = f.read()
    mime, ext = mime_from_file(filepath)
    return FileData(mime=mime, ext=ext, bytes=data)


def read_result(filepath: str, result_type: type[TResult]) -> TResult | None:
    if os.path.isfile(filepath):
        file_data = read_file_data(filepath)
        if file_data is None:
            return None
        return result_type(data=[file_data])
    elif os.path.isdir(filepath):
        files = [read_file_data(str(f)) for f in sorted(Path(filepath).iterdir()) if f.is_file()]
        data = [f for f in files if f is not None]
        return result_type(data=data) if data else None
    return None