from pydantic import Base64Bytes, BaseModel


class FileData(BaseModel):
    mime: str
    ext: str
    bytes: Base64Bytes
    description: str | None = None


class FileResult(BaseModel):
    data: list[FileData]
