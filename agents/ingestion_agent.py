import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import httpx
import sentry_sdk
from supabase import create_client, Client

from agents.observability import init_observability
from scrapers.rss.rss_scraper import scrape_rss
from scrapers.httpx.httpx_scraper import scrape_httpx
from scrapers.playwright.playwright_scraper import scrape_playwright

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

async def process_rss_source(source):
    """
    Scrapes RSS feed, and inserts new articles into the database.
    Does not raise exceptions.
    """
    try:
        insert_data = await scrape_rss(source)
        if not insert_data:
            return

        supabase.table("articles").upsert(insert_data, on_conflict="url", ignore_duplicates=True).execute()
        logger.info(f"[SUCCESS] Ingested {len(insert_data)} articles from RSS source {source['name']}")
    except Exception as e:
        logger.error(f"Failed to process RSS source {source['name']}: {e}")
        sentry_sdk.capture_exception(e)

async def process_httpx_source(source, client: httpx.AsyncClient):
    """
    Scrapes a single static page, checks for duplicates, and inserts.
    """
    try:
        articles = await scrape_httpx(source, client)
        if not articles:
            return

        insert_data = []
        for a in articles:
            insert_data.append({
                "source_id": source["id"],
                "url": a["url"],
                "title": a["title"],
                "raw_html": a["raw_html"],
                "clean_text": a["clean_text"],
                "published_at": None,
                "status": "raw"
            })

        supabase.table("articles").upsert(insert_data, on_conflict="url", ignore_duplicates=True).execute()
        logger.info(f"[SUCCESS] Ingested HTTPX source {source['name']}")
    except Exception as e:
        logger.error(f"Failed to process HTTPX source {source['name']}: {e}")
        sentry_sdk.capture_exception(e)

async def process_playwright_source(source):
    """
    Scrapes a dynamic page using Playwright, checks for duplicates, and inserts.
    """
    try:
        articles = await scrape_playwright(source)
        if not articles:
            return

        insert_data = []
        for a in articles:
            insert_data.append({
                "source_id": source["id"],
                "url": a["url"],
                "title": a["title"],
                "raw_html": a["raw_html"],
                "clean_text": a["clean_text"],
                "published_at": None,
                "status": "raw"
            })

        supabase.table("articles").upsert(insert_data, on_conflict="url", ignore_duplicates=True).execute()
        logger.info(f"[SUCCESS] Ingested Playwright source {source['name']}")
    except Exception as e:
        logger.error(f"Failed to process Playwright source {source['name']}: {e}")
        sentry_sdk.capture_exception(e)

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

        # 4. Run RSS and HTTPX concurrently
        async with httpx.AsyncClient(timeout=30.0) as client:
            rss_tasks = [process_rss_source(s) for s in rss_sources]
            httpx_tasks = [process_httpx_source(s, client) for s in httpx_sources]
            
            logger.info(f"Launching {len(rss_tasks)} RSS tasks and {len(httpx_tasks)} HTTPX tasks concurrently...")
            await asyncio.gather(*(rss_tasks + httpx_tasks), return_exceptions=True)

        # 5. Run Playwright sequentially
        logger.info(f"Launching {len(playwright_sources)} Playwright tasks sequentially...")
        for s in playwright_sources:
            try:
                await process_playwright_source(s)
            except Exception as e:
                logger.error(f"Failed during Playwright scraping of {s['name']}: {e}")

        # 6. Update last_scraped timestamp for all processed sources (even on failures)
        now_str = datetime.now(timezone.utc).isoformat()
        source_ids = [s["id"] for s in to_scrape]
        for s_id in source_ids:
            try:
                supabase.table("sources").update({"last_scraped": now_str}).eq("id", s_id).execute()
            except Exception as e:
                logger.error(f"Failed to update last_scraped for source {s_id}: {e}")

        logger.info("[SUCCESS] Phase 1: Ingestion finished successfully.")

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"[ERROR] Ingestion phase failed: {e}")
        raise e

def run_ingestion():
    asyncio.run(main_ingestion())

if __name__ == "__main__":
    run_ingestion()
