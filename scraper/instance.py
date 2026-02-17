import os
from logging import INFO

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

from utils.logger import get_logger
from utils.url import get_domain


class Scraper:
    def __init__(self, log_level: int = INFO) -> None:
        # Avoid heavy work in __init__; use create() to initialize
        self.logger = get_logger(self.__class__.__name__, level=log_level)
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.mobile_context: BrowserContext | None = None
        self.desktop_context: BrowserContext | None = None
        self.pages: list[Page] = []

    @classmethod
    async def create(cls, log_level: int = INFO) -> "Scraper":
        self = cls(log_level=log_level)
        self.logger.info("Starting Playwright")
        if self.playwright:
            self.logger.warning("Playwright is already initialized")
        else:
            self.playwright = await async_playwright().start()

        self.logger.info("Launching Chromium browser")
        self.browser = await self.playwright.chromium.launch(
            headless=True,
        )

        self.logger.info("Creating browser contexts")
        self.mobile_context = await self.browser.new_context(
            **self.playwright.devices["Galaxy S24"],
        )
        self.desktop_context = await self.browser.new_context(
            **self.playwright.devices["Desktop Chrome HiDPI"],
        )
        self.logger.info("Scraper initialized successfully")
        return self

    async def scrape_into_dataset(self, extra_path: str, url: str) -> None:
        domain = get_domain(url)[1]
        save_dir = f"datasets/images/{extra_path}"
        mobile_path = f"{save_dir}/{domain}_mobile.png"
        desktop_path = f"{save_dir}/{domain}_desktop.png"

        if os.path.exists(mobile_path) and os.path.exists(desktop_path):
            self.logger.info(
                "[%s] Skipping scrape (already exists): %s",
                url,
                domain,
            )
            return

        self.logger.info("[%s] Starting scrape", url)

        if not self.mobile_context or not self.desktop_context:
            self.logger.error("Browser contexts are not initialized")
            raise RuntimeError("Browser contexts are not initialized")

        mobile_page = await self.mobile_context.new_page()
        desktop_page = await self.desktop_context.new_page()
        self.pages.extend([mobile_page, desktop_page])

        try:
            os.makedirs(save_dir, exist_ok=True)

            self.logger.debug("[%s] Preparing mobile page", url)
            await mobile_page.goto(url, wait_until="networkidle")
            self.logger.debug("[%s] Taking mobile screenshot", url)
            await mobile_page.screenshot(path=mobile_path)

            self.logger.debug("[%s] Preparing desktop page", url)
            await desktop_page.goto(url, wait_until="networkidle")
            self.logger.debug("[%s] Taking desktop screenshot", url)
            await desktop_page.screenshot(path=desktop_path)

            self.logger.info(
                "[%s] Screenshots saved: %s, %s",
                url,
                mobile_path,
                desktop_path,
            )
        finally:
            if not mobile_page.is_closed():
                await mobile_page.close()
            if not desktop_page.is_closed():
                await desktop_page.close()
            self.pages = [page for page in self.pages if not page.is_closed()]

    async def close(self):
        self.logger.info("Closing all pages")
        for page in self.pages:
            if not page.is_closed():
                await page.close()
        self.pages.clear()

        self.logger.info("Shutting down scraper")
        if self.mobile_context:
            await self.mobile_context.close()
        if self.desktop_context:
            await self.desktop_context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
