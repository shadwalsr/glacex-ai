import logging
from playwright.async_api import async_playwright
import trafilatura

logger = logging.getLogger(__name__)

async def scrape_playwright(source):
    """
    Scrapes a dynamic web page source using Playwright and extracts clean text using trafilatura.
    """
    url = source["url"]
    name = source["name"]
    logger.info(f"Starting Playwright scrape for {name} ({url})")

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Go to URL with a reasonable timeout (e.g. 45 seconds)
            await page.goto(url, wait_until="networkidle", timeout=45000)
            
            html_content = await page.content()
            title = await page.title()
            
            await browser.close()

            clean_text = trafilatura.extract(html_content)
            if not clean_text:
                clean_text = ""

            return [{
                "title": title or name,
                "url": url,
                "raw_html": html_content,
                "clean_text": clean_text,
                "published_at": None
            }]
    except Exception as e:
        logger.error(f"Error scraping Playwright source {name}: {e}")
        return []
