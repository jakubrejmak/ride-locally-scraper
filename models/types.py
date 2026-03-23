from typing import Literal, Optional

from pydantic import Base64Bytes, BaseModel, Field, model_validator
from typing_extensions import Annotated, Self


class FirecrawlConfig(BaseModel):
    scrape_method: Literal["firecrawl"] = "firecrawl"
    format: Optional[str] = None


class ScraplingConfig(BaseModel):
    scrape_method: Literal["scrapling"] = "scrapling"
    force_mime: Optional[str] = (
        None  # used to force the mime type. If scraped data does not match the format the exception will be raised
    )
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


SupportedLLMModels = Literal["gemini-3-flash-preview"]


class LLMProcessorConfig(BaseModel):
    process_method: Literal["llm"] = "llm"
    llm_model: SupportedLLMModels
    provider: Literal["gemini"]
    system_prompt: Optional[dict[str, str]] = None


class ScrTargetConfig(BaseModel):
    scraper: Annotated[
        FirecrawlConfig | ScraplingConfig, Field(discriminator="scrape_method")
    ]
    processor: Optional[Annotated[LLMProcessorConfig, Field(discriminator="process_method")]] = None


class FileData(BaseModel):
    mime: str
    ext: str
    bytes: Base64Bytes


class ScrRunResult(BaseModel):
    data: list[FileData]


class ProcessResult(BaseModel):
    data: list[FileData]


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
    run_result: Optional[ScrRunResult] = None
