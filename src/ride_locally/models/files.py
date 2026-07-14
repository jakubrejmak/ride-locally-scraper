from pydantic import Base64Bytes, BaseModel

class FileMeta(BaseModel):
    origin_url: str | None = None
    download_timestamp: str | None = None


class FileData(BaseModel):
    file_meta: FileMeta | None = None
    mime: str
    ext: str
    bytes: Base64Bytes
    description: str | None = None


class FileResult(BaseModel):
    data: list[FileData]
