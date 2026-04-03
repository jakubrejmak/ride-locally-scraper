from typing import TypeAlias

from pydantic import Base64Bytes, BaseModel


class FileData(BaseModel):
    mime: str
    ext: str
    bytes: Base64Bytes


class FileResult(BaseModel):
    data: list[FileData]


ScrRunResult: TypeAlias = FileResult
ProcessResult: TypeAlias = FileResult
