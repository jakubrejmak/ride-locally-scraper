from models.files import ScrRunResult
from models.scrapers import FirecrawlConfig


async def run_firecrawl(url: str, config: FirecrawlConfig) -> ScrRunResult | None:
    raise ValueError("firecrawl not implemented yet")
