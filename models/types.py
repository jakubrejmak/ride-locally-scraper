from pydantic import BaseModel, Base64Bytes, model_validator
from typing_extensions import Self
from typing import Literal, Optional


class FirecrawlConfig(BaseModel):
    format: Optional[str] = None


class ScraplingConfig(BaseModel):
    force_mime: Optional[str] = None # used to force the mime type. If scraped data does not match the format the exception will be raised
    fetcher: Literal["AsyncFetcher", "DynamicFetcher", "StealthyFetcher"] = (
        "AsyncFetcher"
    )
    selectors: Optional[list[str]] = None
    script_path: Optional[str] = None

    @model_validator(mode="after")
    def ensure_no_playwright_w_asyncfetcher(self) -> Self:
        if self.fetcher == "AsyncFetcher" and self.script_path:
            raise ValueError(
                "Playwright script path was passed but AsyncFetcher has no playwright compatibility"
            )
        return self


class ScrTargetConfig(BaseModel):
    scrape_method: Literal["firecrawl", "scrapling"]
    firecrawl_conf: Optional[FirecrawlConfig] = None
    scrapling_conf: Optional[ScraplingConfig] = None

    @model_validator(mode="after")
    def ensure_scraper_config(self) -> Self:
        if (
            self.scrape_method == "firecrawl"
            and not self.firecrawl_conf
            or self.scrape_method == "scrapling"
            and not self.scrapling_conf
        ):
            raise ValueError(
                f"Picked scrape method: {self.scrape_method} does not have config associated with it"
            )
        return self


class ScrFileData(BaseModel):
    mime: str
    ext: str
    bytes: Base64Bytes


class ScrTargetResult(BaseModel):
    # list of content keyed by mime type
    data: list[ScrFileData]


class NewScrTarget(BaseModel):
    name: str
    url: str
    config: ScrTargetConfig
    is_active: bool
    schedule_cron: Optional[str] = None
    carrier_id: Optional[int] = None


class ScrScriptResult(BaseModel):
    new_targets: Optional[list[NewScrTarget]] = None  # scripts can add new targets
    self_update: Optional[NewScrTarget] = None  # fields to patch on current target row
    run_result: Optional[ScrTargetResult] = None
