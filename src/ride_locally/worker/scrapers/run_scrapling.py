import importlib.util
import inspect

from scrapling.fetchers import AsyncFetcher, DynamicFetcher, StealthyFetcher

from ride_locally.models.files import FileData, FileResult
from ride_locally.models.scrapers import (
    ScraplingScriptConfig,
    ScraplingSimpleConfig,
)
from ride_locally.models.targets import ScrScriptResult
from ride_locally.worker.files import mime_from_bytes
from ride_locally.worker.scrapers.exceptions import ScraperProcessException


async def _execute_script(filepath: str, url: str) -> ScrScriptResult | None:
    spec = importlib.util.spec_from_file_location("scrapling_script", filepath)
    if not spec or not spec.loader:
        raise ValueError(f"Could not load script from {filepath}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "run"):
        raise ValueError(f"{filepath} must define 'async def run(url)'")
    sig = inspect.signature(module.run)
    if list(sig.parameters) != ["url"]:
        raise ValueError(f"{filepath} must define 'async def run(url)'")

    return await module.run(url)


def _apply_selectors(page, selectors: list[str]) -> bytes:
    fragments: list[str] = []
    for sel in selectors:
        matches = page.css(sel)
        if not matches:
            raise ScraperProcessException(f"Selector matched nothing: {sel!r}")
        for m in matches:
            fragments.append(str(m.html_content))
    return "".join(fragments).encode("utf-8")


async def run_scrapling(
    url: str, config: ScraplingSimpleConfig | ScraplingScriptConfig
) -> FileResult | ScrScriptResult | None:
    if isinstance(config, ScraplingScriptConfig):
        """
        Custom script path needs to return non `None` result in order to qualify for processing.
        It may however intentionally return `None` to perform actions supported by ScrFileResult spec,
        without scheduling a run for processing.
        Scripts can perform arbitrary actions. The only guiderail is they must define `async def run(url)` function.
        """
        return await _execute_script(config.script_path, url)

    match config.fetcher:
        case "AsyncFetcher":
            page = await AsyncFetcher.get(url)
        case "DynamicFetcher":
            page = await DynamicFetcher.async_fetch(url)
        case "StealthyFetcher":
            page = await StealthyFetcher.async_fetch(url)

    if config.selectors:
        # browser transports always render html. AsyncFetcher can hit non-html
        # urls, so validate before parsing.
        source_mime, _ = mime_from_bytes(page.body)
        if source_mime != "text/html":
            raise ScraperProcessException(
                f"Selectors require HTML input, got mime: {source_mime}"
            )
        body = _apply_selectors(page, config.selectors)
        return FileResult(data=[FileData(mime="text/html", ext="html", bytes=body)])

    got_mime, got_ext = mime_from_bytes(page.body)
    if not got_mime:
        raise ScraperProcessException("Content type could not be inferred")
    if config.force_mime and config.force_mime != got_mime:
        raise ValueError(
            f"The forced mime type: '{config.force_mime}' is different than the type got: '{got_mime}'"
        )
    return FileResult(data=[FileData(mime=got_mime, ext=got_ext, bytes=page.body)])
