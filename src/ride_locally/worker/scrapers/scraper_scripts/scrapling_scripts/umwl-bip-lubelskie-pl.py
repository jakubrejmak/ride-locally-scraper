"""This script downloads the excel file with all the timetables from umwl site.
Then adds the timetable links from xlsx as new targets"""

import re
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

import xlrd
from scrapling.engines._browsers._controllers import AsyncDynamicSession
from sqlalchemy import select, update

from ride_locally.db.schema import ScrapeStatus, ScrRunTable, ScrTargetTable
from ride_locally.db.session import session
from ride_locally.models.files import FileData, FileMeta, FileResult
from ride_locally.models.preprocessors import PreprocessorConfig, PreprocessorTool
from ride_locally.models.processors import LLMProcessorConfig, OpenRouterProviderConfig
from ride_locally.models.scrapers import ScraplingSimpleConfig
from ride_locally.models.targets import (
    NewScrTarget,
    ScrRun,
    ScrScriptResult,
    ScrTargetConfig,
)
from ride_locally.worker.files import mime_from_bytes, read_result
from ride_locally.worker.scrapers.exceptions import ScraperProcessException
from ride_locally.worker.utils.scr_target_utils import add_new_targets, get_carrier_id_by
from ride_locally.worker.utils.shared import get_prompt_by_filename

HEADER_MARKERS = (
    "Nazwa Przewoźnika / Operatora",
    "z miejscowości",
    "do miejscowości",
    "przez miejscowości",
    "Rozkład Jazdy",
)
CARRIER_NAME_MARKER = HEADER_MARKERS[0]
NAME_MARKERS = HEADER_MARKERS[:-2]
URL_MARKER = HEADER_MARKERS[-1]

TIMETABLE_TARGET_CONFIG = ScrTargetConfig(
    scraper=ScraplingSimpleConfig(fetcher="AsyncFetcher"),
    preprocessor=PreprocessorConfig(
        tools=[
            PreprocessorTool(
                ref="rotate_to_horizontal",
                params=[
                    {
                        "llm_config": LLMProcessorConfig(
                            config=OpenRouterProviderConfig(
                                system_prompt=get_prompt_by_filename(
                                    "preprocessor", "rotate_to_horizontal.txt"
                                ),
                                user_prompts=[],
                                api_params={},
                                model="gemini-3-flash-preview",
                            )
                        ),
                    }
                ],
            ),
            PreprocessorTool(
                ref="mask_timetable_parts",
                params=[
                    {
                        "llm_config": LLMProcessorConfig(
                            config=OpenRouterProviderConfig(
                                system_prompt=get_prompt_by_filename(
                                    "preprocessor", "timetable_region_detection.txt"
                                ),
                                user_prompts=[],
                                api_params={},
                                model="gemini-3-flash-preview",
                            )
                        ),
                    }
                ],
            ),
        ]
    ),
    processor=LLMProcessorConfig(
        config=OpenRouterProviderConfig(
            system_prompt=get_prompt_by_filename("processor", "transcribe_tables.txt"),
            user_prompts=[],
            api_params={},
            model="gemini-3-flash-preview",
        )
    ),
)


async def disable_targets_by_url(urls: Iterable[str]) -> int:
    async with session() as s:
        stmt = (
            update(ScrTargetTable)
            .where(ScrTargetTable.url.in_(urls))
            .values(
                is_active=False,
                meta={
                    "deactivate_reason": "Stale target: Target url no longer in file."
                },
            )
            .returning(ScrTargetTable.id)
        )
        res = await s.execute(stmt)
        await s.commit()

    updated = res.scalars().all()

    return len(updated)


def _same_site_url(base_url: str, href: str | None) -> str | None:
    if not href or not href.strip():
        return None

    base = urlparse(base_url)
    parsed = urlparse(href)

    # Absolute URL provided
    if parsed.scheme or parsed.netloc:
        # must be same host
        if parsed.netloc.lower() != base.netloc.lower():
            return None

        # keep only path/query/fragment
        href = urlunparse(
            ("", "", parsed.path, parsed.params, parsed.query, parsed.fragment)
        )

    # Build final URL on same site
    final = urljoin(base_url, href)

    if urlparse(final).netloc.lower() != base.netloc.lower():
        return None

    return final


def _normalize(string) -> str:
    return re.sub(r"\s+", " ", str(string).strip().casefold())


def _cell_as_str(sheet, row: int, col: int) -> str:
    """xlrd returns float for numbers, bool for booleans, etc. - normalize to str."""
    cell = sheet.cell(row, col)
    if cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
        return ""
    if cell.ctype == xlrd.XL_CELL_NUMBER:
        value = cell.value
        if value == int(value):
            return str(int(value))
        return str(value)
    return str(cell.value).strip()


def _find_header_row(book: xlrd.Book, header_markers: tuple[str, ...]):
    needles = [_normalize(n) for n in header_markers]

    for i, sheet in enumerate(book.sheets()):
        for r in range(sheet.nrows):
            row_text = " ".join(
                _normalize(_cell_as_str(sheet, r, c)) for c in range(sheet.ncols)
            )
            if all(n in row_text for n in needles):
                return i, r

    return None, None


def _map_header_columns(
    sheet, header_row_no: int, markers: tuple[str, ...]
) -> dict[str, int]:
    col_by_marker: dict[str, int] = {}
    for c in range(sheet.ncols):
        cell = _normalize(_cell_as_str(sheet, header_row_no, c))
        for marker in sorted(markers, key=len, reverse=True):
            if marker in col_by_marker:
                continue
            if _normalize(marker) in cell:
                col_by_marker[marker] = c
                break

    missing = set(markers) - set(col_by_marker)
    if missing:
        raise ScraperProcessException(
            f"Header columns not found for markers: {sorted(missing)}"
        )
    return col_by_marker


def _get_file_bytes(run: ScrRun) -> bytes | None:
    filepath = run.o_filepath

    if not filepath:
        return None

    previous = read_result(filepath, FileResult)

    if not previous or not previous.data:
        return None

    return previous.data[0].bytes


def _get_run_meta(run: ScrRun | None, key: str) -> Any | None:
    if run is None or not run.meta or key not in run.meta:
        return None

    v = run.meta[key]

    return v


async def _get_previous_run_result(scrape_url: str) -> ScrRun | None:
    async with session() as s:
        q = select(ScrTargetTable.id).where(ScrTargetTable.url == scrape_url)
        target_id = (await s.execute(q)).scalar_one_or_none()
        if target_id is None:
            return None

        q = (
            select(ScrRunTable)
            .where(
                ScrRunTable.target_id == target_id,
                ScrRunTable.status == ScrapeStatus.success,
                ScrRunTable.o_filepath.is_not(None),
            )
            .order_by(ScrRunTable.finished_at.desc())
            .limit(1)
        )

        run = (await s.execute(q)).scalar_one_or_none()

        return ScrRun.model_validate(run) if run else None


def _get_row_value_list(sheet, row_no) -> list[str]:
    return [_cell_as_str(sheet, row_no, c) for c in range(sheet.ncols)]


def _find_link(page, url: str, css: str, pattern) -> str | None:
    for a in page.css(css):
        text = re.sub(r"\s+", " ", a.get_all_text()).strip()
        if pattern.search(text):
            raw_href = a.attrib.get("href")
            if not raw_href:
                continue
            return _same_site_url(url, raw_href.strip())
    return None


async def run(url: str) -> ScrScriptResult | None:
    ###
    # 1. find xls download link
    ###

    async with AsyncDynamicSession(
        headless=True, network_idle=True, load_dom=True
    ) as s:
        # https://umwl.bip.lubelskie.pl/index.php?id=848
        page = await s.fetch(url)
        pattern = re.compile(
            r"rozk[łl]ad\w*.*jazdy.*linii.*regularnych.*rozk[łl]ad\w*.*jazdy.*linii.*o.*charakterze.*u[zż]yteczno[sś]ci.*publicznej",
            re.IGNORECASE,
        )
        href = _find_link(page, url, "div.page-submenu a", pattern)
        if not href:
            raise ScraperProcessException("Could not find the timetables submenu link")

        # https://umwl.bip.lubelskie.pl/index.php?id=849
        page = await s.fetch(href)
        pattern = re.compile(r"rozk[łl]ad\W*jazdy", re.IGNORECASE)
        href = _find_link(page, url, "table a", pattern)
        if not href:
            raise ScraperProcessException("Could not find the timetable document link")

        # https://umwl.bip.lubelskie.pl/index.php?id=849&action=details&document_id=...
        page = await s.fetch(href)
        pattern = re.compile(r"\.xls(?:\?|#|$)", re.IGNORECASE)
        download_href = None
        match = None
        for a in page.css(".file-details a"):
            candidate = (a.attrib.get("href") or "").strip()
            match = pattern.search(candidate)
            if match:
                download_href = _same_site_url(url, candidate)
                break
        if not download_href:
            raise ScraperProcessException("Could not find xls download href")

        ###
        # 2a. Check if the previous run's found filename is the same as this one's
        ###

        current_xls_name = download_href[match.start() :] if match else None
        previous_result = await _get_previous_run_result(url)

        last_xls_name = _get_run_meta(previous_result, "last_xls_name") or None

        if (
            last_xls_name is not None
            and current_xls_name is not None
            and last_xls_name == current_xls_name
        ):
            return None  # return if the xls filename is the same as on previous run

        ###
        # 2b. download xls
        ###

        resp = await s.context.request.get(download_href)
        if not resp.ok:
            raise ScraperProcessException(
                f"xls download failed with status {resp.status}"
            )
        body = await resp.body()

        if previous_result is not None and _get_file_bytes(previous_result) == body:
            return None  # return if the previous run's bytes are the same as the downloaded file's

    ###
    # 3. parse xls
    ###

    book = xlrd.open_workbook(file_contents=body, formatting_info=True)
    sheet_no, header_row_no = _find_header_row(book, HEADER_MARKERS)

    if sheet_no is None or header_row_no is None:
        raise ScraperProcessException(
            f"Required header row not found (markers: {HEADER_MARKERS})"
        )

    sheet = book.sheet_by_index(sheet_no)
    column_map = _map_header_columns(sheet, header_row_no, HEADER_MARKERS)

    # build a list of targets discovered in the xsl
    discovered_targets: set[NewScrTarget] = set()
    discovered_target_urls: set[str] = set()
    url_col = column_map[URL_MARKER]
    for r in range(header_row_no + 1, sheet.nrows):
        values = _get_row_value_list(sheet, r)
        hl = sheet.hyperlink_map.get((r, url_col))
        timetable_url = hl.url_or_path if hl else values[url_col]
        assert isinstance(timetable_url, str)
        if not timetable_url:
            continue
        parsed = urlparse(timetable_url)
        if not (parsed.scheme and parsed.netloc):
            timetable_url = urljoin(url, timetable_url)

        name_parts = [
            values[column_map[m]] for m in NAME_MARKERS if values[column_map[m]]
        ]

        # build an array of new scrape targets (urls in xls) discovered by this target
        discovered_target_urls.add(timetable_url)
        carrier_id = await get_carrier_id_by(name=values[column_map[CARRIER_NAME_MARKER]])
        discovered_targets.add(
            NewScrTarget(
                name=" - ".join(name_parts)[:255],
                url=timetable_url,
                config=TIMETABLE_TARGET_CONFIG,
                is_active=False,
                schedule_cron=None,
                carrier_id=carrier_id,
                next_due_at=datetime.now(timezone.utc),
            )
        )

    # deactivate all the previously added targets
    # reason being if the target dissapears from xls - its not longer useful
    previous_targets_urls: set[str] = set(  # used later to scrape stale targets
        _get_run_meta(previous_result, "previously_discovered_urls") or []
    )

    stale_targets_urls = previous_targets_urls - discovered_target_urls
    _ = await disable_targets_by_url(stale_targets_urls)

    # add the built targets to DB
    _ = await add_new_targets(discovered_targets)

    # build this target (umwl) file result (xls with all the links)
    mime, _ = mime_from_bytes(body)
    file_result = FileResult(
        data=[
            FileData(
                mime=mime,
                ext="xls",
                bytes=body,
                file_meta=FileMeta(
                    origin_url=download_href,
                    download_timestamp=str(datetime.now(timezone.utc)),
                ),
            )
        ]
    )

    # return result with downloaded xls
    return ScrScriptResult(
        self_update=None,
        run_file_result=file_result,
        run_meta={
            "last_xls_name": current_xls_name,
            "previously_discovered_urls": discovered_target_urls,
        },
    )
