from typing import Literal

from pydantic import BaseModel


class FirecrawlConfig(BaseModel):
    scrape_method: Literal["firecrawl"] = "firecrawl"
    format: str | None = None
