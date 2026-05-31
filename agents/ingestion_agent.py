import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import sentry_sdk
from supabase import create_client, Client

from agents.observability import init_observability
from scrapers.rss.rss_scraper import scrape_rss
from scrapers.httpx.httpx_scraper import scrape_httpx, fetch_full_page
from scrapers.playwright.playwright_scraper import scrape_playwright
from playwright.async_api import async_playwright

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize Sentry/Langsmith
init_observability()

# Load env vars
load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def parse_db_timestamp(ts_str):
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

async def process_rss_source(source) -> list[dict]:
    """
    Scrapes RSS feed, and returns the scraped articles.
    Does not raise exceptions.
    """
    try:
        insert_data = await scrape_rss(source)
        if not insert_data:
            return []
        logger.info(f"[SUCCESS] Scraped {len(insert_data)} articles from RSS source {source['name']}")
        return insert_data
    except Exception as e:
        logger.error(f"Failed to process RSS source {source['name']}: {e}")
        sentry_sdk.capture_exception(e)
        return []

async def process_httpx_source(source) -> list[dict]:
    """
    Scrapes a single static page and returns results.
    The scraper manages its own httpx.AsyncClient with per-domain rate limiting.
    """
    try:
        articles = await scrape_httpx(source)
        if not articles:
            return []
        logger.info(f"[SUCCESS] Scraped HTTPX source {source['name']}")
        return articles
    except Exception as e:
        logger.error(f"Failed to process HTTPX source {source['name']}: {e}")
        sentry_sdk.capture_exception(e)
        return []

async def process_playwright_source(source, browser) -> list[dict]:
    """
    Scrapes a dynamic page using a shared Playwright Browser instance.
    The browser is created once in main_ingestion and passed here to avoid
    per-source Chromium startup costs.
    """
    try:
        articles = await scrape_playwright(source, browser)
        if not articles:
            return []
        logger.info(f"[SUCCESS] Scraped Playwright source {source['name']}")
        return articles
    except Exception as e:
        logger.error(f"Failed to process Playwright source {source['name']}: {e}")
        sentry_sdk.capture_exception(e)
        return []

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

async def main_ingestion():
    logger.info("Phase 1: Ingestion starting...")
    try:
        # 1. Fetch active sources
        res = supabase.table("sources").select("*").eq("active", True).execute()
        sources = res.data

        # 2. Filter: only scrape sources not hit in last 5.5 hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=5.5)
        to_scrape = []
        for s in sources:
            last_scraped_dt = parse_db_timestamp(s.get("last_scraped"))
            if last_scraped_dt is None or last_scraped_dt < cutoff:
                to_scrape.append(s)

        logger.info(f"Found {len(sources)} active sources. {len(to_scrape)} scheduled for scraping.")
        if not to_scrape:
            logger.info("No sources scheduled to scrape. Exiting.")
            return

        # 3. Partition
        rss_sources = [s for s in to_scrape if s["type"] == "rss"]
        httpx_sources = [s for s in to_scrape if s["type"] == "httpx"]
        playwright_sources = [s for s in to_scrape if s["type"] == "playwright"]

        all_scraped = []

        # 4. Run RSS and HTTPX concurrently
        # httpx_scraper owns its client; pass source dict only
        rss_tasks = [process_rss_source(s) for s in rss_sources]
        httpx_tasks = [process_httpx_source(s) for s in httpx_sources]

        if rss_tasks or httpx_tasks:
            logger.info(f"Launching {len(rss_tasks)} RSS tasks and {len(httpx_tasks)} HTTPX tasks concurrently...")
            results = await asyncio.gather(*(rss_tasks + httpx_tasks), return_exceptions=True)
            for r in results:
                if isinstance(r, list):
                    all_scraped.extend(r)
                elif isinstance(r, Exception):
                    logger.error(f"A concurrent scraper task failed with exception: {r}")

        # 5. Run Playwright sources sequentially, sharing ONE browser instance
        #    --no-sandbox is required on GitHub Actions (Linux non-root runner)
        #    --disable-gpu avoids Mesa/rendering issues in headless CI
        if playwright_sources:
            logger.info(f"Launching {len(playwright_sources)} Playwright tasks sequentially (shared browser)...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-gpu"]
                )
                try:
                    for s in playwright_sources:
                        articles = await process_playwright_source(s, browser)
                        all_scraped.extend(articles)
                finally:
                    await browser.close()
        else:
            logger.info("No Playwright sources scheduled.")

        # 6. Deduplicate against known URLs in the database
        logger.info(f"Scraped {len(all_scraped)} total articles. Loading known URLs from Supabase...")
        try:
            db_res = supabase.table("articles").select("url").execute()
            known_urls = {r["url"] for r in db_res.data if r.get("url")}
        except Exception as e:
            logger.error(f"Failed to fetch known URLs from Supabase: {e}")
            known_urls = set()

        new_items = [
            item for item in all_scraped
            if item.get("url") and item["url"] not in known_urls
        ]
        logger.info(f"Filtered down to {len(new_items)} new articles to insert.")

        # 6.5. Enrich new RSS articles with full page content (excluding arXiv)
        rss_source_ids = {s["id"] for s in rss_sources}
        arxiv_source_ids = {s["id"] for s in rss_sources if "arxiv.org" in s["url"].lower()}

        async def enrich_rss_item(item):
            if item["source_id"] in rss_source_ids and item["source_id"] not in arxiv_source_ids:
                logger.info(f"Enriching RSS item: {item['url']}")
                clean, raw_html = await fetch_full_page(item["url"])
                if clean:
                    item["clean_text"] = clean
                    item["raw_html"] = raw_html
                else:
                    logger.warning(f"Could not retrieve full content for {item['url']}; keeping feed summary.")

        enrich_tasks = [enrich_rss_item(item) for item in new_items]
        if enrich_tasks:
            logger.info(f"Concurrently fetching full page content for {len(enrich_tasks)} new RSS items...")
            await asyncio.gather(*enrich_tasks, return_exceptions=True)

        # 7. Bulk insert new items in chunks of 500
        inserted_count = 0
        for chunk in chunks(new_items, 500):
            try:
                supabase.table("articles").upsert(chunk, on_conflict="url").execute()
                inserted_count += len(chunk)
            except Exception as e:
                logger.error(f"Failed to upsert chunk of {len(chunk)} items: {e}")
                sentry_sdk.capture_exception(e)

        logger.info(f"[SUCCESS] Successfully ingested {inserted_count} new articles.")

        # 8. Update sources.last_scraped and ingestion metrics. Mark every source as completed.
        now_str = datetime.utcnow().isoformat()
        for source in to_scrape:
            try:
                supabase.table("sources").update({
                    "last_scraped": now_str
                }).eq("id", source["id"]).execute()
            except Exception as e:
                logger.error(f"Failed to update last_scraped for source {source['id']}: {e}")

        # Log ingestion summary
        print(f"Ingested: {inserted_count} new articles from {len(to_scrape)} sources")
        logger.info("[SUCCESS] Phase 1: Ingestion finished successfully.")

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"[ERROR] Ingestion phase failed: {e}")
        raise e

def run_ingestion():
    asyncio.run(main_ingestion())

if __name__ == "__main__":
    run_ingestion()
