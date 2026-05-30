import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import httpx
import trafilatura
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

async def fetch_full_content(url, client: httpx.AsyncClient, semaphore: asyncio.Semaphore):
    """
    Helper to fetch raw HTML and extract clean text from an article URL with concurrency limit.
    """
    async with semaphore:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            response = await client.get(url, headers=headers, follow_redirects=True, timeout=20.0)
            if response.status_code == 200:
                raw_html = response.text
                clean_text = trafilatura.extract(raw_html) or ""
                return raw_html, clean_text
        except Exception as e:
            logger.warning(f"Failed to fetch content for {url}: {e}")
        return None, None

async def process_rss_source(source, client: httpx.AsyncClient, semaphore: asyncio.Semaphore):
    """
    Scrapes RSS feed, checks DB for new articles, fetches body for new ones, and inserts.
    """
    source_id = source["id"]
    feed_articles = await scrape_rss(source, client)
    if not feed_articles:
        return

    # Check which URLs already exist in the database
    urls = [a["url"] for a in feed_articles]
    try:
        existing_res = supabase.table("articles").select("url").in_("url", urls).execute()
        existing_urls = {r["url"] for r in existing_res.data}
    except Exception as e:
        logger.error(f"Error checking existing URLs for {source['name']}: {e}")
        existing_urls = set()

    # Filter out existing articles
    new_articles = [a for a in feed_articles if a["url"] not in existing_urls]
    # Limit number of parallel fetches to avoid rate limits
    new_articles = new_articles[:15]

    if not new_articles:
        logger.info(f"No new articles to fetch for RSS source: {source['name']}")
        return

    logger.info(f"Fetching full body for {len(new_articles)} new articles from {source['name']}")
    
    # Concurrently fetch full page content for new articles
    tasks = [fetch_full_content(a["url"], client, semaphore) for a in new_articles]
    results = await asyncio.gather(*tasks)

    insert_data = []
    for article, (raw_html, clean_text) in zip(new_articles, results):
        pub_at = article["published_at"].isoformat() if article["published_at"] else None
        insert_data.append({
            "source_id": source_id,
            "url": article["url"],
            "title": article["title"],
            "raw_html": raw_html,
            "clean_text": clean_text,
            "published_at": pub_at,
            "status": "raw"
        })

    if insert_data:
        try:
            supabase.table("articles").upsert(insert_data, on_conflict="url", ignore_duplicates=True).execute()
            logger.info(f"[SUCCESS] Ingested {len(insert_data)} articles from RSS source {source['name']}")
        except Exception as e:
            logger.error(f"Failed to insert articles for {source['name']}: {e}")

async def process_httpx_source(source, client: httpx.AsyncClient):
    """
    Scrapes a single static page, checks for duplicates, and inserts.
    """
    source_id = source["id"]
    articles = await scrape_httpx(source, client)
    if not articles:
        return

    insert_data = []
    for a in articles:
        insert_data.append({
            "source_id": source_id,
            "url": a["url"],
            "title": a["title"],
            "raw_html": a["raw_html"],
            "clean_text": a["clean_text"],
            "published_at": None,
            "status": "raw"
        })

    try:
        supabase.table("articles").upsert(insert_data, on_conflict="url", ignore_duplicates=True).execute()
        logger.info(f"[SUCCESS] Ingested HTTPX source {source['name']}")
    except Exception as e:
        logger.error(f"Failed to insert HTTPX source {source['name']}: {e}")

async def process_playwright_source(source):
    """
    Scrapes a dynamic page using Playwright, checks for duplicates, and inserts.
    """
    source_id = source["id"]
    articles = await scrape_playwright(source)
    if not articles:
        return

    insert_data = []
    for a in articles:
        insert_data.append({
            "source_id": source_id,
            "url": a["url"],
            "title": a["title"],
            "raw_html": a["raw_html"],
            "clean_text": a["clean_text"],
            "published_at": None,
            "status": "raw"
        })

    try:
        supabase.table("articles").upsert(insert_data, on_conflict="url", ignore_duplicates=True).execute()
        logger.info(f"[SUCCESS] Ingested Playwright source {source['name']}")
    except Exception as e:
        logger.error(f"Failed to insert Playwright source {source['name']}: {e}")

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

        # Limit concurrency for network fetches
        semaphore = asyncio.Semaphore(5)

        # 4. Run RSS and HTTPX concurrently
        async with httpx.AsyncClient(timeout=30.0) as client:
            rss_tasks = [process_rss_source(s, client, semaphore) for s in rss_sources]
            httpx_tasks = [process_httpx_source(s, client) for s in httpx_sources]
            
            logger.info(f"Launching {len(rss_tasks)} RSS tasks and {len(httpx_tasks)} HTTPX tasks concurrently...")
            await asyncio.gather(*(rss_tasks + httpx_tasks), return_exceptions=True)

        # 5. Run Playwright sequentially (since browser is single-threaded / resource heavy)
        logger.info(f"Launching {len(playwright_sources)} Playwright tasks sequentially...")
        for s in playwright_sources:
            try:
                await process_playwright_source(s)
            except Exception as e:
                logger.error(f"Failed during Playwright scraping of {s['name']}: {e}")

        # 6. Update last_scraped timestamp for all processed sources
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
