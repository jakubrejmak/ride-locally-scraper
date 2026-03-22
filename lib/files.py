import magic
import mimetypes
import os


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
