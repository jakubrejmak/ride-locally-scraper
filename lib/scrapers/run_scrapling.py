from models.types import ScraplingConfig, ScrTargetResult
from scrapling.fetchers import AsyncFetcher, DynamicFetcher, StealthyFetcher

FETCHERS = {
    "AsyncFetcher": AsyncFetcher,
    "DynamicFetcher": DynamicFetcher,
    "StealthyFetcher": StealthyFetcher,
}

async def _execute_script(fetcher: type[DynamicFetcher | StealthyFetcher], filepath: str, url: str):
    pass

async def run_scrapling(url: str, config: ScraplingConfig) -> ScrTargetResult | None:
    fetcher = FETCHERS[config.fetcher]
    if config.playwright_script_path and fetcher is not AsyncFetcher:
        # playwright path
        result = await _execute_script(fetcher, config.playwright_script_path, url)
    elif config.selectors:
        # selector paths
        pass
    else:
        # get whole page
        async def _fetch(fetcher, url: str):
            if fetcher is AsyncFetcher:
                return fetcher.get(url)
            return fetcher.async_fetch(url)

        result = await _fetch(fetcher, url=url)

    pass