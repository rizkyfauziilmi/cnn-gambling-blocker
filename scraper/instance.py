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
        self.pages: list[Page] = []

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
        self.logger.info("Scraper initialized successfully")
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

    async def _remove_overlays_and_modal(self, page: Page, url: str) -> None:
        """Remove common overlay elements like modals and pop-ups using MutationObserver.

        Strategy:
        - Inject a small script into the page (and all frames) that:
          - clicks likely "close" / "accept" buttons (by text or aria-label),
          - removes elements that look like overlays/modals based on heuristics
            (role=dialog, aria-modal, common class/id names, fixed/absolute with high z-index),
          - sets up a MutationObserver to remove newly added overlays for a short window.
        - Wait briefly to allow the page to stabilize after removals.

        The method is defensive: it ignores exceptions from page/frame evaluation
        and logs debug information when removal fails.
        """  # noqa: E501
        js_cleanup = """
        () => {
          const removeElement = (el) => {
            try { el.remove(); } catch (e) {}
          };

          const safeTextMatches = (s) => {
            if (!s) return false;
            const t = s.toString().toLowerCase().trim();
            return /(^|\\s)(close|dismiss|accept|agree|allow|got it|gotit|ok|okay|no thanks|skip|continue|x)(\\s|$)/i.test(t);
          };

          // Single regex to detect modal/overlay/popup-like tokens anywhere inside a class or id (case-insensitive).
          // This will match 'notifModal', 'backgroundOverlay', 'site-popup-123', etc.
          const hint = /(modal|overlay|popup|pop-?up|cookie|consent|banner|subscribe|subscription|newsletter|lightbox|dialog)/i;

          const looksLikeHeader = (el, rect) => {
            try {
              if (!rect) rect = el.getBoundingClientRect();
              // very top, short height and wide -> likely header/nav
              if (rect.top <= 40 && rect.height < window.innerHeight * 0.25 && rect.width >= window.innerWidth * 0.5) return true;
              // contains semantic nav
              if (el.querySelector && el.querySelector('nav, [role="navigation"]')) return true;
            } catch (e) {}
            return false;
          };

          const isOverlay = (el) => {
            try {
              if (!(el instanceof HTMLElement)) return false;
              const tag = (el.tagName || '').toString().toLowerCase();
              const style = window.getComputedStyle(el) || {};
              const pos = style.position || "";
              const zIndex = Number(style.zIndex || 0) || 0;
              const pointerEvents = style.pointerEvents || '';
              const visibility = style.visibility || '';
              const opacity = Number(style.opacity || 1);
              const classes = (el.className || "").toString().toLowerCase();
              const id = (el.id || "").toString().toLowerCase();
              const role = (el.getAttribute && el.getAttribute('role') || "").toString().toLowerCase();
              const ariaModal = (el.getAttribute && el.getAttribute('aria-modal')) || "";

              // Never remove semantic nav/header/footer or elements clearly part of site chrome.
              if (tag === 'nav' || tag === 'header' || tag === 'footer') return false;
              if (role === 'navigation') return false;
              if (/\b(nav|navbar|site-nav|main-nav|topbar|site-header|header|masthead)\b/.test(classes)) return false;

              // If element or ancestors include nav/header/footer, treat as chrome not overlay
              try {
                if (el.closest && el.closest('nav, header, footer')) return false;
              } catch (e) {}

              const rect = el.getBoundingClientRect();

              // If element appears to be a header/band at the top, avoid removing it
              if (looksLikeHeader(el, rect)) return false;

              // If element is hidden or non-interactive, skip
              if (pointerEvents === 'none') return false;
              if (visibility === 'hidden' || opacity === 0) return false;

              // Strong signals for dialogs that we should remove
              if (role === 'dialog' || ariaModal === 'true') return true;

              // hint regex is defined above (shared); reuse it here

              const coversMajority = (rect.width >= window.innerWidth * 0.6 && rect.height >= window.innerHeight * 0.6);

              // If class/id hint exists, require either a substantial z-index or substantial coverage
              if (hint.test(classes) || hint.test(id)) {
                if ((pos === 'fixed' || pos === 'sticky' || pos === 'absolute') && zIndex >= 800) {
                  if (rect.width < 60 && rect.height < 60) return false;
                  // wide but short bars at top are likely navbars; skip them
                  if (rect.height < 200 && rect.width >= window.innerWidth * 0.6 && rect.top <= (window.innerHeight * 0.25)) return false;
                  return true;
                }
                if (coversMajority) return true;
              }

              // If element is fixed/sticky with an extremely high z-index and not header-like, consider removing
              if ((pos === 'fixed' || pos === 'sticky' || pos === 'absolute') && zIndex >= 2000) {
                if (rect.width < 50 && rect.height < 50) return false;
                if (rect.height < 200 && rect.width >= window.innerWidth * 0.6 && rect.top <= (window.innerHeight * 0.25)) return false;
                return true;
              }

              // If it covers majority and has some stacking, remove
              if (coversMajority && zIndex > 0) return true;

              return false;
            } catch (e) {
              return false;
            }
          };

          // Try clicking close/accept buttons but only when they're clearly within an overlay-like ancestor
          try {
            const candidates = Array.from(document.querySelectorAll('button, a, [role="button"], input[type="button"], input[type="submit"]'));
            candidates.forEach((btn) => {
              try {
                const label = (btn.innerText || btn.value || (btn.getAttribute && btn.getAttribute('aria-label')) || '').toString();
                if (!safeTextMatches(label)) return;
                // ensure the button is within an element that looks like overlay or dialog
                let p = btn;
                let foundOverlayAncestor = false;
                for (let i = 0; i < 6 && p; i++) {
                  try {
                    if (p === document.body) break;
                    if (isOverlay(p)) { foundOverlayAncestor = true; break; }
                    p = p.parentElement;
                  } catch (e) { break; }
                }
                if (foundOverlayAncestor) {
                  try { btn.click(); } catch (e) {}
                }
              } catch (e) {}
            });
          } catch (e) {}

          // Remove overlays present now, but be conservative
          try {
            const all = Array.from(document.body ? document.body.querySelectorAll('*') : []);
            // iterate from leaves to root to avoid removing ancestors before children
            all.reverse().forEach((el) => {
              try {
                if (isOverlay(el)) removeElement(el);
              } catch (e) {}
            });
          } catch (e) {}

          // Observe for newly added nodes and remove overlays for a short period
          try {
            const observer = new MutationObserver((mutations) => {
              for (const m of mutations) {
                for (const node of m.addedNodes) {
                  try {
                    if (node.nodeType === 1) {
                      try {
                        if (isOverlay(node)) removeElement(node);
                        if (node.querySelectorAll) {
                          const nested = Array.from(node.querySelectorAll('*'));
                          // remove nested overlays conservatively
                          nested.reverse().forEach((el) => {
                            try { if (isOverlay(el)) removeElement(el); } catch (e) {}
                          });
                        }
                      } catch (e) {}
                    }
                  } catch (e) {}
                }
              }
            });
            observer.observe(document.documentElement || document, { childList: true, subtree: true, attributes: false });
            // stop observing after 8s
            setTimeout(() => {
              try { observer.disconnect(); } catch (e) {}
            }, 8000);
          } catch (e) {}
        }
        """  # noqa: E501

        try:
            # Inject and run cleanup in main frame
            try:
                self.logger.debug(f"[{url}] Removing overlays and modals")
                await page.evaluate(js_cleanup)
            except Exception as e:
                self.logger.debug("[%s] Main frame cleanup failed: %s", url, e)

            # Also attempt to run cleanup in all child frames (if any)
            try:
                for frame in page.frames:
                    # skip main frame as we've already tried it; compare by url
                    try:
                        if frame == page.main_frame:
                            continue
                        # Some frames may be cross-origin and fail evaluation; ignore errors  # noqa: E501
                        await frame.evaluate(js_cleanup)
                    except Exception:
                        # best-effort: ignore per-frame failures
                        pass
            except Exception as e:
                self.logger.debug("[%s] Frame iteration failed: %s", url, e)

            # Give the page a short moment to settle after removals
            try:
                await page.wait_for_timeout(800)
            except Exception:
                # Non-critical if wait fails
                pass

        except Exception as e:
            self.logger.debug("[%s] Failed to remove overlays and modals: %s", url, e)
        finally:
            self.logger.debug(f"[{url}] Overlay and modal removal complete")

    async def _wait_images_in_viewport(self, page: Page) -> None:
        """Wait for images that are visible in the current viewport (above the fold) to finish loading.

        This checks both <img> elements and CSS background-image URLs on elements that intersect
        the viewport. It is best-effort: it resolves after either all visible images load/error
        or after the timeout elapses.
        """  # noqa: E501
        js_wait_images = """
        (timeoutMs) => new Promise((resolve) => {
          try {
            const imgs = Array.from(document.images || []);

            const visibleImgs = imgs.filter((img) => {
              try {
                const r = img.getBoundingClientRect();
                return !(r.bottom <= 0 || r.top >= window.innerHeight || r.right <= 0 || r.left >= window.innerWidth);
              } catch (e) { return false; }
            });

            // Find background-image URLs for visible elements
            const elems = Array.from(document.querySelectorAll('*'));
            const bgUrls = new Set();
            elems.forEach((el) => {
              try {
                const r = el.getBoundingClientRect();
                if (r.bottom <= 0 || r.top >= window.innerHeight || r.right <= 0 || r.left >= window.innerWidth) return;
                const style = window.getComputedStyle(el);
                const bg = style && style.backgroundImage;
                if (bg && bg !== 'none') {
                  const m = bg.match(/url\\((?:\\"|\\')?(.*?)(?:\\"|\\')?\\)/);
                  if (m && m[1]) bgUrls.add(m[1]);
                }
              } catch (e) {}
            });

            const urls = Array.from(bgUrls);

            let remaining = visibleImgs.length + urls.length;
            if (remaining === 0) return resolve(true);

            const finishOne = () => {
              remaining -= 1;
              if (remaining <= 0) resolve(true);
            };

            visibleImgs.forEach((img) => {
              try {
                if (img.complete) return finishOne();
                const onload = () => { finishOne(); cleanup(); };
                const onerr = () => { finishOne(); cleanup(); };
                const cleanup = () => { try { img.removeEventListener('load', onload); img.removeEventListener('error', onerr); } catch (e) {} };
                img.addEventListener('load', onload);
                img.addEventListener('error', onerr);
              } catch (e) { finishOne(); }
            });

            urls.forEach((u) => {
              try {
                const i = new Image();
                const onload = () => { finishOne(); cleanup(); };
                const onerr = () => { finishOne(); cleanup(); };
                const cleanup = () => { try { i.removeEventListener('load', onload); i.removeEventListener('error', onerr); } catch (e) {} };
                i.addEventListener('load', onload);
                i.addEventListener('error', onerr);
                i.src = u;
              } catch (e) { finishOne(); }
            });

            // timeout fallback
            setTimeout(() => { resolve(true); }, Math.max(100, timeoutMs));

          } catch (e) {
            resolve(true);
          }
        })
        """  # noqa: E501

        try:
            self.logger.debug(f"[{page.url or '<unknown>'}] Waiting for viewport images to load")
            await page.evaluate(js_wait_images)
        except Exception as e:
            self.logger.debug(
                "Failed waiting for viewport images on %s: %s",
                page.url or "<unknown>",
                e,
            )
        finally:
            self.logger.debug(f"[{page.url or '<unknown>'}] Wait for viewport images complete")

    async def _prepare_page_for_screenshot(self, page: Page, url: str) -> None:
        page.on("dialog", self._handle_dialog)
        try:
            await page.goto(url=url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            self.logger.warning(f"[{url}] Failed to navigate to page: {e}")
        await self._remove_overlays_and_modal(page, url)
        await self._wait_images_in_viewport(page)

    async def scrape_into_dataset(self, extra_path: str, url: str) -> None:
        _, domain = get_domain(url)
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

        if not is_accessible_html(url):
            self.logger.warning(
                "[%s] URL is not accessible or does not return HTML content",
                url,
            )
            raise RuntimeError(f"URL not accessible or non-HTML: {url}")

        self.logger.info("[%s] Starting scrape", url)

        if not self.mobile_context or not self.desktop_context:
            self.logger.error("Browser contexts are not initialized")
            raise RuntimeError("Browser contexts are not initialized")

        mobile_page = await self.mobile_context.new_page()
        desktop_page = await self.desktop_context.new_page()
        self.pages.extend([mobile_page, desktop_page])

        try:
            self.logger.debug("[%s] Preparing mobile page", url)
            await self._prepare_page_for_screenshot(mobile_page, url)
            self.logger.debug("[%s] Preparing desktop page", url)
            await self._prepare_page_for_screenshot(desktop_page, url)

            os.makedirs(save_dir, exist_ok=True)
            self.logger.debug("[%s] Taking mobile screenshot", url)
            await mobile_page.screenshot(path=mobile_path)
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
