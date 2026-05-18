from models.files import FileResult
from models.scrapers import FirecrawlConfig


async def run_firecrawl(url: str, config: FirecrawlConfig) -> FileResult | None:
    raise ValueError("firecrawl not implemented yet")
