from typing import Literal
import magic
import mimetypes
import os


def chck_type(
    media: str | bytes,
    method: Literal["from_url", "from_file", "from_path", "from_bytes"] = "from_path",
    mime_opts: Literal["full", "ext_only", "none"] = "full",
) -> str | None:
    get_mime = True if mime_opts != "none" else False

    if method == "from_bytes" and not isinstance(media, bytes):
        raise ValueError(f"Method '{method}' not compatible with media type '{type(media)}'")

    def strip_prefix(mimetype: str) -> str:
        no_pfx = mimetype.split("/")[1]
        return no_pfx

    match method:
        case "from_file":
            assert isinstance(media, str)
            if not os.path.isfile(media):
                raise ValueError(f"Method {method} expected a valid file, got: {media}")
            ext = magic.from_file(media, mime=get_mime)
        case "from_bytes":
            assert isinstance(media, bytes)
            ext = magic.from_buffer(media, mime=get_mime)
        case "from_path":
            assert isinstance(media, str)
            ext = os.path.splitext(media)[1].lstrip(".")
            if mime_opts == "full":
                return mimetypes.guess_type(media)[0]
            return ext or None
        case "from_url":
            assert isinstance(media, str)
            path = media.split("?")[0]
            ext = os.path.splitext(path)[1].lstrip(".")
            if mime_opts == "full":
                return mimetypes.guess_type(path)[0]
            return ext or None

    if mime_opts == "ext_only":
        return strip_prefix(ext)
    return ext
