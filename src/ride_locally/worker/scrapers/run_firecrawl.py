from ride_locally.models.FirecrawlConfig import FirecrawlConfig
from ride_locally.models.files import FileResult


async def run_firecrawl(url: str, config: FirecrawlConfig) -> FileResult | None:
    raise ValueError("firecrawl not implemented yet")
