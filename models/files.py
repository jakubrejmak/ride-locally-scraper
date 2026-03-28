from pydantic import Base64Bytes, BaseModel


class FileData(BaseModel):
    mime: str
    ext: str
    bytes: Base64Bytes


class ScrRunResult(BaseModel):
    data: list[FileData]


class ProcessResult(BaseModel):
    data: list[FileData]