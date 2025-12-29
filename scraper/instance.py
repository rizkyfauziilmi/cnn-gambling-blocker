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
from utils.url import get_domain, is_accessible_html


class Scraper:
    def __init__(self, log_level: int = INFO) -> None:
        # Avoid heavy work in __init__; use create() to initialize
        self.logger = get_logger(self.__class__.__name__, level=log_level)
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.mobile_context: BrowserContext | None = None
        self.desktop_context: BrowserContext | None = None

    @classmethod
    async def create(cls, log_level: int = INFO) -> "Scraper":
        self = cls(log_level=log_level)
        self.logger.info("Starting Playwright")
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
        return self

    async def _handle_dialog(self, dialog) -> None:
        self.logger.debug(
            "Dialog detected: type=%s message=%s",
            dialog.type,
            dialog.message,
        )
        try:
            await dialog.accept()
        except Exception as e:
            self.logger.debug(f"Failed to accept dialog: {e}")

    async def _remove_overlays(self, page: Page, url: str) -> None:
        """Remove common overlay elements like modals and pop-ups using MutationObserver."""  # noqa: E501
        overlay_selectors = [
            'div[class*="modal" i]',
            'div[class*="popup" i]',
            'div[class*="pop-up" i]',
            'div[class*="dialog" i]',
            'div[class*="bg-black" i]',
            'div[id*="dialog" i]',
            'div[id*="modal" i]',
            'div[id*="popup" i]',
            'div[id*="pop-up" i]',
            'div[id*="bg-black" i]',
            # ARIA roles
            'div[role="dialog"]',
            'div[role="alertdialog"]',
            'div[role="presentation"]',
            # Data attributes
            "div[data-modal]",
            "div[data-dialog]",
        ]
        selectors_str = ", ".join(overlay_selectors)

        try:
            await page.evaluate(
                f"""
                () => {{
                    const removeOverlays = () => {{
                        const selectors = ['{selectors_str.replace("'", "\\'")}'];
                        selectors.forEach(selector => {{
                            document.querySelectorAll(selector).forEach(el => {{
                                el.remove();
                            }});
                        }});
                        // Remove based on z-index
                        document.querySelectorAll('div[style*="z-index"]').forEach(el => {{
                            const zIndex = window.getComputedStyle(el).zIndex;
                            const classList = el.className.toLowerCase();
                            const isNavbar = /navbar|header|menu|nav/.test(classList);
                            if (zIndex && parseInt(zIndex) >= 1000 && !isNavbar) {{
                                el.remove();
                            }}
                        }});
                    }};
                    // Debounce helper to avoid running removeOverlays on every mutation
                    const debounce = (fn, delay) => {{
                        let timerId;
                        return (...args) => {{
                            clearTimeout(timerId);
                            timerId = setTimeout(() => fn.apply(null, args), delay);
                        }};
                    }};
                    const debouncedRemoveOverlays = debounce(removeOverlays, 200);
                    // Initial removal
                    removeOverlays();
                    // Watch for dynamically added overlays
                    const observer = new MutationObserver(() => {{
                        debouncedRemoveOverlays();
                    }});
                    observer.observe(document.body, {{
                        childList: true,
                        subtree: true,
                    }});
                }}
                """  # noqa: E501
            )
            self.logger.debug(
                f"[{url}] MutationObserver set up for dynamic overlay removal"
            )
        except Exception as e:
            self.logger.warning(
                f"[{url}] Error setting up MutationObserver for overlays: {e}"
            )

    async def _prepare_page_for_screenshot(self, page: Page, url: str) -> None:
        page.on("dialog", self._handle_dialog)
        try:
            await page.goto(url=url, wait_until="networkidle", timeout=30_000)
        except Exception as e:
            self.logger.warning(f"[{url}] Failed to navigate to page: {e}")
        await self._remove_overlays(page, url)

    async def scrape_into_dataset(self, extra_path: str, url: str) -> None:
        url_normalized, domain = get_domain(url)
        save_dir = f"datasets/{extra_path}"
        mobile_path = f"{save_dir}/{domain}_mobile.png"
        desktop_path = f"{save_dir}/{domain}_desktop.png"

        if os.path.exists(mobile_path) and os.path.exists(desktop_path):
            self.logger.info(
                "[%s] Skipping scrape (already exists): %s",
                url_normalized,
                domain,
            )
            return

        self.logger.info("[%s] Starting scrape", url_normalized)

        if not is_accessible_html(url_normalized):
            self.logger.error("[%s] URL not accessible or not HTML", url_normalized)
            raise ValueError(f"URL not accessible: {url_normalized}")

        if not self.mobile_context or not self.desktop_context:
            self.logger.error("Browser contexts are not initialized")
            raise RuntimeError("Browser contexts are not initialized")

        mobile_page = await self.mobile_context.new_page()
        desktop_page = await self.desktop_context.new_page()

        try:
            self.logger.debug("[%s] Preparing mobile page", url_normalized)
            await self._prepare_page_for_screenshot(mobile_page, url_normalized)
            self.logger.debug("[%s] Preparing desktop page", url_normalized)
            await self._prepare_page_for_screenshot(desktop_page, url_normalized)

            os.makedirs(save_dir, exist_ok=True)
            self.logger.debug("[%s] Taking mobile screenshot", url_normalized)
            await mobile_page.screenshot(path=mobile_path)
            self.logger.debug("[%s] Taking desktop screenshot", url_normalized)
            await desktop_page.screenshot(path=desktop_path)

            self.logger.info(
                "[%s] Screenshots saved: %s, %s",
                url,
                mobile_path,
                desktop_path,
            )
        finally:
            await mobile_page.close()
            await desktop_page.close()

    async def scrape_into_bytes(self, url: str) -> tuple[bytes, bytes]:
        url_normalized, domain = get_domain(url)

        self.logger.info("[%s] Starting scrape into bytes", url_normalized)

        if not is_accessible_html(url_normalized):
            self.logger.error("[%s] URL not accessible or not HTML", url_normalized)
            raise ValueError(f"URL not accessible: {url_normalized}")

        if not self.mobile_context or not self.desktop_context:
            self.logger.error("Browser contexts are not initialized")
            raise RuntimeError("Browser contexts are not initialized")

        mobile_page = await self.mobile_context.new_page()
        desktop_page = await self.desktop_context.new_page()

        try:
            self.logger.debug("[%s] Preparing mobile page", url_normalized)
            await self._prepare_page_for_screenshot(mobile_page, url_normalized)
            self.logger.debug("[%s] Preparing desktop page", url_normalized)
            await self._prepare_page_for_screenshot(desktop_page, url_normalized)

            self.logger.debug("[%s] Taking mobile screenshot", url_normalized)
            mobile_bytes = await mobile_page.screenshot()
            self.logger.debug("[%s] Taking desktop screenshot", url_normalized)
            desktop_bytes = await desktop_page.screenshot()

            self.logger.info(
                "[%s] Screenshots captured in bytes for domain: %s",
                url,
                domain,
            )
            return mobile_bytes, desktop_bytes
        finally:
            await mobile_page.close()
            await desktop_page.close()

    async def close(self):
        self.logger.info("Shutting down scraper")
        if self.mobile_context:
            await self.mobile_context.close()
        if self.desktop_context:
            await self.desktop_context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
