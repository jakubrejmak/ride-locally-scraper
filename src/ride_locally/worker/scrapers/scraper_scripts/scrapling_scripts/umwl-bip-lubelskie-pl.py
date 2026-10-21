"""This script downloads the Excel file with all the timetables from umwl site.
Then adds the timetable links from xlsx as new targets"""

import re
from collections.abc import Generator
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from io import BytesIO
from typing import ClassVar
from urllib.parse import urljoin, urlparse, urlunparse

import openpyxl
import xlrd
from scrapling.engines._browsers._controllers import AsyncDynamicSession

from ride_locally.models.ScraperScriptResult import ScrScriptResult
from ride_locally.models.ScraperTarget import NewScrTarget
from ride_locally.models.ScraperTargetConfig import ScrTargetConfig
from ride_locally.models.files import FileData, FileMeta, FileResult
from ride_locally.worker.files import mime_from_bytes
from ride_locally.worker.scrapers.exceptions import ScraperProcessException
from ride_locally.worker.utils.openpyxl_helpers import OpenpyxlHelper
from ride_locally.worker.utils.scr_run_utils import (
    get_file_bytes,
    get_previous_run_result_by,
    get_run_meta,
)
from ride_locally.worker.utils.scr_target_utils import add_new_targets, \
    disable_targets_by_url, get_carrier_id_by
from ride_locally.worker.utils.table_search import TableSearch
from ride_locally.worker.utils.xlrd_helpers import XlrdHelper


@dataclass(frozen=True)
class UMWLHeader:
    """Column index of each field in the source sheet."""

    # header text each field's column is located by
    MARKERS: ClassVar[dict[str, str]] = {
        "carrier_name": "Nazwa Przewoźnika / Operatora",
        "origin": "z miejscowości",
        "destination": "do miejscowości",
        "via": "przez miejscowości",
        "timetable_url": "Rozkład Jazdy",
    }

    carrier_name: int
    origin: int
    destination: int
    via: int
    timetable_url: int


class UMWLSheet:
    def __init__(self) -> None:
        self.header_row: UMWLHeader | None = None
        self.data_rows: list[tuple[str, ...]] = []

    def set_header(self, header: UMWLHeader) -> None:
        self.header_row = header

    def append(self, row: tuple[str, ...]) -> None:
        self.data_rows.append(row)

    def get_row(self) -> Generator[dict[str, str], None, None]:
        """Yields each row keyed by UMWLHeader field name."""
        if self.header_row is None:
            raise ValueError("No header row")

        columns = asdict(self.header_row)
        for row in self.data_rows:
            yield {field: row[col] for field, col in columns.items()}


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
            raise ScraperProcessException(
                "Could not find the timetables submenu link")

        # https://umwl.bip.lubelskie.pl/index.php?id=849
        page = await s.fetch(href)
        pattern = re.compile(r"rozk[łl]ad\W*jazdy", re.IGNORECASE)
        href = _find_link(page, url, "table a", pattern)
        if not href:
            raise ScraperProcessException(
                "Could not find the timetable document link")

        # https://umwl.bip.lubelskie.pl/index.php?id=849&action=details&document_id=...
        page = await s.fetch(href)
        pattern = re.compile(r"\.xlsx?(?:\?|#|$)", re.IGNORECASE)
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

        current_xls_name = download_href[match.start():] if match else None
        previous_result = await get_previous_run_result_by(url)

        last_xls_name = get_run_meta(previous_result, "last_xls_name") or None

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

        if previous_result is not None and get_file_bytes(
                previous_result) == body:
            return None  # return if the previous run's bytes are the same as the downloaded file's

    ###
    # 3. parse xls or xlsx
    ###

    sheet = UMWLSheet()
    match (mime_from_bytes(body)):
        case _, "vnd.ms-excel":
            file_ext = "xls"
            book = xlrd.open_workbook(file_contents=body, formatting_info=True)
            native_sheets = book.sheets()
            helper = XlrdHelper
            index_base = 0
        case _, "vnd.openxmlformats-officedocument.spreadsheetml.sheet":
            file_ext = "xlsx"
            # data_only: formula cells give their cached value, as xlrd does
            wb = openpyxl.load_workbook(BytesIO(body), data_only=True)
            native_sheets = wb.worksheets
            helper = OpenpyxlHelper
            index_base = 1
        case _:
            raise ScraperProcessException("Unsupported file type")

    # both helpers expose the same get_rows/get_hyperlink
    sheet_rows = [helper.get_rows(s) for s in native_sheets]
    markers = UMWLHeader.MARKERS
    sheet_no, header_row_no = TableSearch.find_row(sheet_rows, markers.values())
    if sheet_no is None or header_row_no is None:
        raise ScraperProcessException(
            f"Required header row not found (markers: {tuple(markers.values())})"
        )
    rows = sheet_rows[sheet_no]

    columns = TableSearch.find_columns(rows[header_row_no], markers)
    missing = markers.keys() - columns.keys()
    if missing:
        raise ScraperProcessException(
            f"Header columns not found for markers: {sorted(markers[k] for k in missing)}"
        )
    header = UMWLHeader(**columns)
    sheet.set_header(header)

    for r in range(header_row_no + 1, len(rows)):
        values = rows[r]
        # get_rows lists are 0-based, get_hyperlink takes the library's own indexing
        # (xlrd counts from 0, openpyxl from 1)
        link = helper.get_hyperlink(
            native_sheets[sheet_no], r + index_base, header.timetable_url + index_base
        )
        if link:
            values[header.timetable_url] = link
        sheet.append(tuple(values))

    # build a list of targets discovered in the xls, keyed by url to drop duplicates
    discovered_targets: dict[str, NewScrTarget] = {}

    for target in sheet.get_row():
        timetable_url = target["timetable_url"]
        assert isinstance(timetable_url, str)
        if not timetable_url:
            continue
        parsed = urlparse(timetable_url)
        if not (parsed.scheme and parsed.netloc):
            timetable_url = urljoin(url, timetable_url)

        name_parts = [
            target[f] for f in ("carrier_name", "origin", "destination") if target[f]
        ]

        # build an array of new scrape targets (urls in xls) discovered by this target
        carrier_id = await get_carrier_id_by(name=target["carrier_name"])
        discovered_targets[timetable_url] = NewScrTarget(
            name=" - ".join(name_parts)[:255],
            url=timetable_url,
            config=ScrTargetConfig.from_preset("default_new_target"),
            is_active=False,
            schedule_cron=None,
            carrier_id=carrier_id,
            next_due_at=datetime.now(timezone.utc),
        )

    # deactivate all the previously added targets
    # reason being if the target disappears from xls - it's no longer useful
    previous_targets_urls: set[str] = set(  # used later to scrape stale targets
        get_run_meta(previous_result, "previously_discovered_urls") or []
    )

    stale_targets_urls = previous_targets_urls - discovered_targets.keys()
    _ = await disable_targets_by_url(
        stale_targets_urls, reason="Stale target: Target url no longer in file."
    )

    # add the built targets to DB
    _ = await add_new_targets(discovered_targets.values())

    # build this target (umwl) file result (xls with all the links)
    mime, _ = mime_from_bytes(body)
    file_result = FileResult(
        data=[
            FileData(
                mime=mime,
                ext=file_ext,
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
            "previously_discovered_urls": set(discovered_targets),
        },
    )
