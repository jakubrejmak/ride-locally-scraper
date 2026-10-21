from typing import Annotated, Literal

from pydantic import Field, BaseModel, ConfigDict, model_validator
from typing_extensions import Self


class ScraplingScriptConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scrape_method: Literal["scrapling"] = "scrapling"
    mode: Literal["script"] = "script"
    script_path: str


class ScraplingSimpleConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scrape_method: Literal["scrapling"] = "scrapling"
    mode: Literal["simple"] = "simple"
    fetcher: Literal["AsyncFetcher", "DynamicFetcher", "StealthyFetcher"] = (
        "AsyncFetcher"
    )
    selectors: list[str] | None = None
    force_mime: str | None = (
        None  # used to force the mime type. If scraped data does not match the format the exception will be raised
    )

    @model_validator(mode="after")
    def _no_force_mime_with_selectors(self) -> Self:
        if self.selectors and self.force_mime:
            raise ValueError(
                "force_mime is meaningless when selectors are set (output is always text/html)"
            )
        return self


ScraplingConfig = Annotated[
    ScraplingSimpleConfig | ScraplingScriptConfig,
    Field(discriminator="mode"),
]
