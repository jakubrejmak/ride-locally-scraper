from typing import Literal

from pydantic import BaseModel, model_validator
from typing_extensions import Self


class FirecrawlConfig(BaseModel):
    scrape_method: Literal["firecrawl"] = "firecrawl"
    format: str | None = None


class ScraplingConfig(BaseModel):
    scrape_method: Literal["scrapling"] = "scrapling"
    force_mime: str | None = (
        None  # used to force the mime type. If scraped data does not match the format the exception will be raised
    )
    fetcher: Literal["AsyncFetcher", "DynamicFetcher", "StealthyFetcher"] = (
        "AsyncFetcher"
    )
    selectors: list[str] | None = None
    script_path: str | None = None

    @model_validator(mode="after")
    def ensure_no_playwright_w_asyncfetcher(self) -> Self:
        if self.fetcher == "AsyncFetcher" and self.script_path:
            raise ValueError(
                "Playwright script path was passed but AsyncFetcher has no playwright compatibility"
            )
        return self
