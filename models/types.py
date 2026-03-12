from pydantic import BaseModel, Base64Bytes, model_validator
from typing_extensions import Self
from typing import Literal, Optional


class FirecrawlConfig(BaseModel):
    pass


class ScraplingConfig(BaseModel):
    pass


class ScrTargetConfig(BaseModel):
    scrape_method: Literal["firecrawl", "scrapling"]
    table_format: Optional[Literal["text", "image", "pdf"]] = None
    selectors: Optional[list[str]] = None
    playwright_script_path: Optional[str] = None
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

class ScrTargetResult(BaseModel):
    text_parts: list[str]
    images: list[Base64Bytes]