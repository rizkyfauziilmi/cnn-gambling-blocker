import os
from logging import INFO

from playwright.sync_api import sync_playwright

from libs.url import get_domain, is_accessible_html
from logger_pkg.logger import get_logger


# TODO: handle dimmed backgrounds, consent popups
class Scraper:
    def __init__(self, log_level: int = INFO) -> None:
        self.logger = get_logger(name=self.__class__.__name__, level=log_level)

        self.logger.info("Starting Playwright")
        self.playwright = sync_playwright().start()

        self.logger.info("Launching Chromium browser (headless)")
        self.browser = self.playwright.chromium.launch(headless=True)

        self.logger.info("Creating mobile and desktop contexts")
        self.mobile_context = self.browser.new_context(**self.playwright.devices["Galaxy S24"])
        self.desktop_context = self.browser.new_context(**self.playwright.devices["Desktop Chrome HiDPI"])

    def _handle_dialog(self, dialog) -> None:
        """Handle browser dialogs (alerts, confirms, prompts)"""
        self.logger.info(f"Dialog detected: {dialog.type} - {dialog.message}")
        dialog.accept()

    def _remove_overlays(self, page) -> None:
        """Remove common overlays and popups from the page"""
        try:
            overlay_selectors = [
                "[role='dialog']",
                ".modal",
                ".popup",
                ".overlay",
                ".advertisement",
                "[class*='cookie']",
                "[class*='consent']",
                "[class*='banner']",
            ]
            for selector in overlay_selectors:
                try:
                    page.locator(selector).evaluate_all("els => els.forEach(el => el.remove())")
                except Exception:
                    continue
            self.logger.debug("Overlays removed")
        except Exception as e:
            self.logger.warning(f"Could not remove overlays: {e}")

    def _remove_dimmed_background(self, page) -> None:
        """Remove dimmed background overlays based on CSS properties"""
        try:
            page.locator("body *").evaluate_all(
                """
                els => els.forEach(el => {
                    const style = window.getComputedStyle(el);
                    const isBg = style.position === 'fixed' &&
                                 style.zIndex >= 1000 &&
                                 (style.backgroundColor.includes('rgba(0, 0, 0,') ||
                                  style.backgroundColor === 'rgb(0, 0, 0)');
                    if (isBg) el.remove();
                })
                """
            )
            self.logger.debug("Dimmed backgrounds removed")
        except Exception as e:
            self.logger.warning(f"Could not remove dimmed backgrounds: {e}")

    def scrape_into_dataset(self, extra_path: str, url: str) -> None:
        self.logger.info(f"Scraping into dataset: {url}")

        mobile_page = self.mobile_context.new_page()
        desktop_page = self.desktop_context.new_page()

        mobile_page.on("dialog", self._handle_dialog)
        desktop_page.on("dialog", self._handle_dialog)

        if not is_accessible_html(url):
            self.logger.error(f"URL not accessible or not HTML: {url}")
            raise ValueError("The provided URL is not accessible or does not return HTML content.")

        url, domain = get_domain(url)
        self.logger.debug(f"Normalized URL: {url}")

        self.logger.info("Navigating pages")
        mobile_page.goto(url, wait_until="domcontentloaded")
        desktop_page.goto(url, wait_until="domcontentloaded")

        self.logger.info("Removing overlays and dimmed backgrounds from pages")
        self._remove_overlays(mobile_page)
        self._remove_overlays(desktop_page)
        self._remove_dimmed_background(mobile_page)
        self._remove_dimmed_background(desktop_page)

        save_path = f"datasets/{extra_path}"
        os.makedirs(save_path, exist_ok=True)
        self.logger.info(f"Saving screenshots to {save_path}")

        mobile_path = f"{save_path}/{domain}_mobile.png"
        desktop_path = f"{save_path}/{domain}_desktop.png"

        mobile_page.screenshot(path=mobile_path)
        desktop_page.screenshot(path=desktop_path)
        self.logger.info(f"Screenshots saved: {mobile_path}, {desktop_path}")

        mobile_page.close()
        desktop_page.close()

    def scrape_into_bytes(self, url: str) -> tuple[bytes, bytes]:
        self.logger.info(f"Scraping into bytes: {url}")

        mobile_page = self.mobile_context.new_page()
        desktop_page = self.desktop_context.new_page()

        mobile_page.on("dialog", self._handle_dialog)
        desktop_page.on("dialog", self._handle_dialog)

        if not is_accessible_html(url):
            self.logger.error(f"URL not accessible or not HTML: {url}")
            raise ValueError("The provided URL is not accessible or does not return HTML content.")

        url, _ = get_domain(url)
        self.logger.debug(f"Normalized URL: {url}")

        self.logger.info("Navigating pages")
        mobile_page.goto(url, wait_until="domcontentloaded")
        desktop_page.goto(url, wait_until="domcontentloaded")

        self.logger.info("Removing overlays and dimmed backgrounds from pages")
        self._remove_overlays(mobile_page)
        self._remove_overlays(desktop_page)
        self._remove_dimmed_background(mobile_page)
        self._remove_dimmed_background(desktop_page)

        self.logger.info("Taking screenshots as bytes")
        mobile_screenshot = mobile_page.screenshot()
        desktop_screenshot = desktop_page.screenshot()
        self.logger.info("Screenshots captured successfully")

        mobile_page.close()
        desktop_page.close()

        return mobile_screenshot, desktop_screenshot

    def _remove_instance(self):
        self.logger.info("Closing browser contexts and Playwright")
        self.mobile_context.close()
        self.desktop_context.close()
        self.browser.close()
        self.playwright.stop()

    def close(self):
        self._remove_instance()
