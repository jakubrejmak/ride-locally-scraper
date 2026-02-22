import importlib
import os
import uuid
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import Page, async_playwright

from database.models import ContentType

DATA_DIR = os.getenv("DATA_DIR", "data")


class ScrapeResult:
    def __init__(self, paths: list[str], content_type: ContentType):
        self.paths = paths
        self.content_type = content_type


class ContentContext:
    """Chainable API for narrowing, extracting, and saving scraped content.

    Each select() narrows the scope further. All save/download
    operations use the current scope.

    Usage in a custom script:

        async def run(page, ctx, config):
            await page.click("#load-more")
            ctx.reload(await page.content())
            ctx.select("#timetable").select(".active-tab")
            return await ctx.download_images()
    """

    def __init__(self, html: str, base_url: str, headers: dict | None = None, timeout: int = 30):
        self._base_url = base_url
        self._headers = headers or {}
        self._timeout = timeout
        self._soup = BeautifulSoup(html, "html.parser")
        self._scope = self._soup

    def reload(self, html: str) -> "ContentContext":
        self._soup = BeautifulSoup(html, "html.parser")
        self._scope = self._soup
        return self

    def select(self, selector: str) -> "ContentContext":
        element = self._scope.select_one(selector)
        if element:
            self._scope = element
        return self

    def html(self) -> str:
        return str(self._scope)

    def image_urls(self) -> list[str]:
        imgs = self._scope.find_all("img", src=True)
        return [urljoin(self._base_url, str(img.get("src"))) for img in imgs]

    def save_html(self) -> ScrapeResult:
        path = self._save(self.html().encode(), "html")
        return ScrapeResult([path], ContentType.html)

    async def download_images(self) -> ScrapeResult:
        urls = self.image_urls()
        if not urls:
            return self.save_html()
        paths = []
        async with httpx.AsyncClient(timeout=self._timeout, headers=self._headers) as client:
            for url in urls:
                resp = await client.get(url)
                resp.raise_for_status()
                ct = resp.headers.get("content-type", "")
                ext = ct.split("/")[-1].split(";")[0] if "image" in ct else "png"
                paths.append(self._save(resp.content, ext))
        return ScrapeResult(paths, ContentType.img)

    def save_bytes(self, data: bytes, ext: str) -> ScrapeResult:
        path = self._save(data, ext)
        return ScrapeResult([path], ContentType.img)

    async def screenshot(self, page: "Page", selector: str | None = None) -> ScrapeResult:
        if selector:
            elements = await page.query_selector_all(selector)
            if elements:
                paths = [self._save(await el.screenshot(), "png") for el in elements]
                return ScrapeResult(paths, ContentType.img)
        return self.save_bytes(await page.screenshot(full_page=True), "png")

    def _save(self, data: bytes, ext: str) -> str:
        os.makedirs(DATA_DIR, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.{ext}"
        path = os.path.join(DATA_DIR, filename)
        with open(path, "wb") as f:
            f.write(data)
        return path


class Scrape:
    def __init__(self, url: str, config: dict):
        self.url = url
        self.config = config
        self.fetch_method = config.get("fetch_method", "http")
        self.content_mode = config.get("content_mode", "html")
        self.selector = config.get("selector")
        self.headers = config.get("headers", {})
        self.timeout = config.get("timeout", 30)
        self.script = config.get("script")

        if self.content_mode == "screenshot" and self.fetch_method != "playwright":
            raise ValueError("content_mode 'screenshot' requires fetch_method 'playwright'")

    def _make_ctx(self, html: str) -> ContentContext:
        return ContentContext(html, self.url, self.headers, self.timeout)

    async def _fetch_http(self) -> ScrapeResult:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(self.url, headers=self.headers)
            resp.raise_for_status()

            if "image" in resp.headers.get("content-type", ""):
                ext = resp.headers["content-type"].split("/")[-1].split(";")[0]
                return self._make_ctx("").save_bytes(resp.content, ext)

            ctx = self._make_ctx(resp.text)
            if self.selector:
                ctx.select(self.selector)

            if self.content_mode == "download":
                return await ctx.download_images()

            return ctx.save_html()

    async def _fetch_playwright(self) -> ScrapeResult:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page()
            if self.headers:
                await page.set_extra_http_headers(self.headers)
            await page.goto(self.url, timeout=self.timeout * 1000)
            await page.wait_for_load_state("networkidle")

            ctx = self._make_ctx(await page.content())

            script_name = self.script or "default"
            script_fn = importlib.import_module(f"data.pw_scripts.{script_name}").run
            result = await script_fn(page, ctx, self.config)

            await browser.close()
            return result

    async def fetch(self) -> ScrapeResult:
        match self.fetch_method:
            case "http":
                return await self._fetch_http()
            case "playwright":
                return await self._fetch_playwright()
            case _:
                raise ValueError(f"Unknown fetch method: {self.fetch_method}")
