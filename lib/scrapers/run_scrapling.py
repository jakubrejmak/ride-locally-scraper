import importlib.util
import inspect
from models.types import ScraplingConfig, ScrTargetResult, ScrScriptResult
from scrapling.fetchers import AsyncFetcher, DynamicFetcher, StealthyFetcher
from lib.files import chck_type

FETCHERS = {
    "AsyncFetcher": AsyncFetcher,
    "DynamicFetcher": DynamicFetcher,
    "StealthyFetcher": StealthyFetcher,
}


async def _execute_script(
    fetcher: type[DynamicFetcher | StealthyFetcher], filepath: str, url: str
) -> ScrScriptResult | None:
    spec = importlib.util.spec_from_file_location("scrapling_script", filepath)
    if not spec or not spec.loader:
        raise ValueError(f"Could not load script from {filepath}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "run"):
        raise ValueError(f"{filepath} must define 'async def run(fetcher, url)'")

    sig = inspect.signature(module.run)
    if list(sig.parameters) != ["fetcher", "url"]:
        raise ValueError(f"{filepath} must define 'async def run(fetcher, url)'")

    return await module.run(fetcher, url)


async def run_scrapling(
    url: str, config: ScraplingConfig
) -> ScrTargetResult | ScrScriptResult | None:
    fetcher = FETCHERS[config.fetcher]

    def _fetch(fetcher, url: str):
        if fetcher is AsyncFetcher:
            return fetcher.get(url)
        return fetcher.async_fetch(url)

    result: ScrScriptResult | ScrTargetResult | None = None
    if config.script_path and fetcher is not AsyncFetcher:
        # custom script path
        result = await _execute_script(fetcher, config.script_path, url)
    elif config.selectors:
        # TODO selector paths
        for s in config.selectors:
            pass
    else:
        # TODO get whole page
        page = await _fetch(fetcher, url=url)
        expected = config.force_mime
        actual = chck_type(page.body, "from_bytes", "full")
        if expected and expected != actual:
            raise ValueError(f"The forced mime type '{expected}' is different than the actual type '{actual}'")

    return result
