import logging
import trafilatura
import sentry_sdk
from playwright.async_api import Browser

logger = logging.getLogger(__name__)

# Resource types to block — images, fonts, and stylesheets slow page loads
# significantly without contributing any textual content.
BLOCKED_RESOURCE_TYPES = {"image", "stylesheet", "font", "media"}

async def _block_resources(route, request):
    """Route handler: abort blocked resource types, allow everything else."""
    if request.resource_type in BLOCKED_RESOURCE_TYPES:
        await route.abort()
    else:
        await route.continue_()

async def scrape_playwright(source: dict, browser: Browser) -> list[dict]:
    """
    Scrapes a dynamic web page using an existing Playwright Browser instance.

    Key design rules:
    - Browser is created ONCE in the orchestrator and reused across all sources
      (saves ~1-2s per source in Chromium startup cost).
    - Images, fonts, stylesheets, and media are blocked via the route API.
    - Supports source-specific CSS selectors via scrape_config.item_selector.
    - Page timeout is hard-capped at 30 000 ms; JS settle wait is 2 000 ms.
    - Never raises — all exceptions are captured to Sentry and return [].
    """
    url = source["url"]
    name = source.get("name", url)
    cfg = source.get("scrape_config") or {}

    try:
        page = await browser.new_page(
            user_agent="Mozilla/5.0 GlaceX/1.0"
        )

        # Block heavy resources to speed up page loads
        await page.route("**/*", _block_resources)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30_000)
            await page.wait_for_timeout(2_000)  # JS settle time

            item_selector = cfg.get("item_selector")

            if item_selector:
                # --- Selector mode: extract individual link items ---
                items = await page.query_selector_all(item_selector)
                results = []
                for item in items[:30]:  # cap at 30 items per source
                    try:
                        text = (await item.inner_text()).strip()
                        href = await item.get_attribute("href") or url
                        # Make relative URLs absolute
                        if href.startswith("/"):
                            from urllib.parse import urlparse
                            parsed = urlparse(url)
                            href = f"{parsed.scheme}://{parsed.netloc}{href}"
                        if text:
                            results.append({
                                "source_id": source["id"],
                                "url": href,
                                "title": text[:500],
                                "raw_html": "",
                                "clean_text": text,
                                "published_at": None,
                                "status": "raw",
                            })
                    except Exception as item_err:
                        logger.warning(f"Failed to extract item from {name}: {item_err}")
                        continue

                logger.info(f"Playwright [selector] scraped {len(results)} items from {name}")
                return results

            else:
                # --- Fallback mode: extract full page content ---
                html = await page.content()
                clean = trafilatura.extract(
                    html,
                    include_comments=False,
                    include_tables=True,
                    favor_recall=True,
                    output_format="markdown",
                )

                if not clean or len(clean) < 200:
                    logger.info(f"Skipping {name} — extracted text too short (< 200 chars).")
                    return []

                title = await page.title()
                logger.info(f"Playwright [full-page] scraped {len(clean)} chars from {name}")
                return [{
                    "source_id": source["id"],
                    "url": url,
                    "title": title or name,
                    "raw_html": html[:50_000],  # cap raw HTML storage
                    "clean_text": clean,
                    "published_at": None,
                    "status": "raw",
                }]

        finally:
            await page.close()

    except Exception as e:
        logger.error(f"Error scraping Playwright source {name}: {e}")
        sentry_sdk.capture_exception(e)
        return []
