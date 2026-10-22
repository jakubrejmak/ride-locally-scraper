from typing import Any, Generic, Optional, TypeVar

from pydantic import BaseModel, RootModel, model_validator
from typing_extensions import Self


class MetaEntry(BaseModel, frozen=True):
    code: str


EntryT = TypeVar("EntryT", bound=MetaEntry)


class MetaField(RootModel[Optional[dict[str, EntryT | None]]], Generic[EntryT]):
    root: dict[str, EntryT | None] | None = None

    @model_validator(mode="before")
    @classmethod
    def _code_from_key(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        return {
            code: {**entry, "code": code} if isinstance(entry, dict) else entry
            for code, entry in data.items()
        }

    def add(self, entry: EntryT) -> None:
        self.root = {**(self.root or {}), entry.code: entry}

    def update(self, other: Self) -> None:
        for code, entry in (other.root or {}).items():
            if entry is None:
                self.remove(code)
            else:
                self.add(entry)

    def remove(self, code: str) -> None:
        self.root = {k: v for k, v in (self.root or {}).items() if
                     k != code} or None

    def remove_all(self) -> None:
        self.root = None
