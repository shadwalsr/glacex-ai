import os
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
import sentry_sdk
from supabase import create_client, Client

from agents.observability import init_observability, init_pipeline_run, update_pipeline_run_metric, resolve_active_run_id, start_phase_checkpoint, complete_phase_checkpoint, is_phase_completed
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

def log_ingestion_outcome(source_id: str, status: str, items_scraped: int, error_message: str = None):
    try:
        supabase.table("raw_ingestion_log").insert({
            "source_id": source_id,
            "status": status,
            "items_scraped": items_scraped,
            "error_message": error_message,
            "duration_s": 0
        }).execute()
    except Exception as e:
        logger.error(f"Failed to write to raw_ingestion_log: {e}")

async def process_rss_source(source) -> tuple[list[dict], bool]:
    """
    Scrapes RSS feed, and returns the scraped articles and success status.
    """
    from urllib.parse import urlparse
    from agents.circuit_breaker import PersistentCircuitBreaker, CircuitBreakerOpenException
    parsed = urlparse(source.get("url") or "")
    domain = parsed.netloc or "unknown"
    breaker = PersistentCircuitBreaker(f"scraped_site:{domain}")
    try:
        async def do_scrape():
            return await scrape_rss(source)
        
        insert_data = await breaker.call_async(do_scrape)
        logger.info(f"[SUCCESS] Scraped {len(insert_data) if insert_data else 0} articles from RSS source {source['name']}")
        log_ingestion_outcome(source["id"], "success", len(insert_data) if insert_data else 0)
        return (insert_data or []), True
    except CircuitBreakerOpenException:
        logger.warning(f"Circuit breaker for scraped_site:{domain} is OPEN. Bypassing source {source['name']}.")
        log_ingestion_outcome(source["id"], "bypassed", 0, f"Circuit breaker '{domain}' is OPEN")
        return [], False
    except Exception as e:
        logger.error(f"Failed to process RSS source {source['name']}: {e}")
        sentry_sdk.capture_exception(e)
        log_ingestion_outcome(source["id"], "failed", 0, str(e))
        return [], False

async def process_httpx_source(source) -> tuple[list[dict], bool]:
    """
    Scrapes a single static page and returns results and success status.
    """
    from urllib.parse import urlparse
    from agents.circuit_breaker import PersistentCircuitBreaker, CircuitBreakerOpenException
    parsed = urlparse(source.get("url") or "")
    domain = parsed.netloc or "unknown"
    breaker = PersistentCircuitBreaker(f"scraped_site:{domain}")
    try:
        async def do_scrape():
            return await scrape_httpx(source)
            
        articles = await breaker.call_async(do_scrape)
        logger.info(f"[SUCCESS] Scraped HTTPX source {source['name']}")
        log_ingestion_outcome(source["id"], "success", len(articles) if articles else 0)
        return (articles or []), True
    except CircuitBreakerOpenException:
        logger.warning(f"Circuit breaker for scraped_site:{domain} is OPEN. Bypassing source {source['name']}.")
        log_ingestion_outcome(source["id"], "bypassed", 0, f"Circuit breaker '{domain}' is OPEN")
        return [], False
    except Exception as e:
        logger.error(f"Failed to process HTTPX source {source['name']}: {e}")
        sentry_sdk.capture_exception(e)
        log_ingestion_outcome(source["id"], "failed", 0, str(e))
        return [], False

async def process_playwright_source(source, browser) -> tuple[list[dict], bool]:
    """
    Scrapes a dynamic page using a shared Playwright Browser instance.
    """
    from urllib.parse import urlparse
    from agents.circuit_breaker import PersistentCircuitBreaker, CircuitBreakerOpenException
    parsed = urlparse(source.get("url") or "")
    domain = parsed.netloc or "unknown"
    breaker = PersistentCircuitBreaker(f"scraped_site:{domain}")
    try:
        async def do_scrape():
            return await scrape_playwright(source, browser)
            
        articles = await breaker.call_async(do_scrape)
        logger.info(f"[SUCCESS] Scraped Playwright source {source['name']}")
        log_ingestion_outcome(source["id"], "success", len(articles) if articles else 0)
        return (articles or []), True
    except CircuitBreakerOpenException:
        logger.warning(f"Circuit breaker for scraped_site:{domain} is OPEN. Bypassing source {source['name']}.")
        log_ingestion_outcome(source["id"], "bypassed", 0, f"Circuit breaker '{domain}' is OPEN")
        return [], False
    except Exception as e:
        logger.error(f"Failed to process Playwright source {source['name']}: {e}")
        sentry_sdk.capture_exception(e)
        log_ingestion_outcome(source["id"], "failed", 0, str(e))
        return [], False

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

async def main_ingestion():
    logger.info("Phase 1: Ingestion starting...")
    # Initialize pipeline run tracking state locally or resume
    run_id = resolve_active_run_id()
    logger.info(f"Using pipeline run id: {run_id}")
    
    if is_phase_completed(run_id, "ingest"):
        logger.info("Phase 1 (ingest) already completed for this run. Skipping.")
        return
        
    start_phase_checkpoint(run_id, "ingest")
    
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
            update_pipeline_run_metric(sources_total=0, sources_successful=0, ingested=0)
            complete_phase_checkpoint(run_id, "ingest", 0)
            return

        # 3. Partition
        rss_sources = [s for s in to_scrape if s["type"] == "rss"]
        httpx_sources = [s for s in to_scrape if s["type"] == "httpx"]
        playwright_sources = [s for s in to_scrape if s["type"] == "playwright"]

        all_scraped = []
        sources_total = len(to_scrape)
        sources_successful = 0

        # 4. Run RSS and HTTPX concurrently
        rss_tasks = [process_rss_source(s) for s in rss_sources]
        httpx_tasks = [process_httpx_source(s) for s in httpx_sources]

        if rss_tasks or httpx_tasks:
            logger.info(f"Launching {len(rss_tasks)} RSS tasks and {len(httpx_tasks)} HTTPX tasks concurrently...")
            results = await asyncio.gather(*(rss_tasks + httpx_tasks), return_exceptions=True)
            for r in results:
                if isinstance(r, tuple):
                    articles, success = r
                    all_scraped.extend(articles)
                    if success:
                        sources_successful += 1
                elif isinstance(r, Exception):
                    logger.error(f"A concurrent scraper task failed with exception: {r}")

        # 5. Run Playwright sources concurrently, sharing ONE browser instance
        if playwright_sources:
            logger.info(f"Launching {len(playwright_sources)} Playwright tasks concurrently (shared browser)...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-gpu"]
                )
                try:
                    pw_tasks = [process_playwright_source(s, browser) for s in playwright_sources]
                    results = await asyncio.gather(*pw_tasks, return_exceptions=True)
                    for idx, r in enumerate(results):
                        s = playwright_sources[idx]
                        if isinstance(r, tuple):
                            articles, success = r
                            all_scraped.extend(articles)
                            if success:
                                sources_successful += 1
                        elif isinstance(r, Exception):
                            logger.error(f"Playwright scraper for {s['name']} failed with exception: {r}")
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
                from urllib.parse import urlparse
                from agents.circuit_breaker import PersistentCircuitBreaker, CircuitBreakerOpenException
                parsed = urlparse(item.get("url") or "")
                domain = parsed.netloc or "unknown"
                breaker = PersistentCircuitBreaker(f"scraped_site:{domain}")
                try:
                    async def do_fetch():
                        return await fetch_full_page(item["url"])
                    
                    logger.info(f"Enriching RSS item: {item['url']}")
                    res = await breaker.call_async(do_fetch)
                    if res and isinstance(res, tuple) and len(res) == 2:
                        clean, raw_html = res
                        if clean:
                            item["clean_text"] = clean
                            item["raw_html"] = raw_html
                        else:
                            logger.warning(f"Could not retrieve full content for {item['url']}; keeping feed summary.")
                except CircuitBreakerOpenException:
                    logger.warning(f"Circuit breaker for scraped_site:{domain} is OPEN. Bypassing enrichment for {item['url']}.")
                except Exception as e:
                    logger.warning(f"Failed to enrich item {item['url']}: {e}")

        enrich_tasks = [enrich_rss_item(item) for item in new_items]
        if enrich_tasks:
            logger.info(f"Concurrently fetching full page content for {len(enrich_tasks)} new RSS items...")
            await asyncio.gather(*enrich_tasks, return_exceptions=True)

        # 7. Bulk insert new items in chunks of 500 using text_hash upsert
        import hashlib
        for item in new_items:
            content = item.get("clean_text") or item.get("title") or ""
            item["text_hash"] = hashlib.sha256(content.encode("utf-8")).hexdigest()

        inserted_count = 0
        for chunk in chunks(new_items, 500):
            try:
                supabase.rpc("bulk_upsert_articles", {"p_articles": chunk}).execute()
                inserted_count += len(chunk)
            except Exception as e:
                logger.error(f"Failed to upsert chunk of {len(chunk)} items: {e}")
                sentry_sdk.capture_exception(e)

        logger.info(f"[SUCCESS] Successfully ingested {inserted_count} new articles.")
        update_pipeline_run_metric(
            sources_total=sources_total,
            sources_successful=sources_successful,
            ingested=inserted_count
        )

        # 8. Update sources.last_scraped. Mark every source as completed.
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
        complete_phase_checkpoint(run_id, "ingest", inserted_count)

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"[ERROR] Ingestion phase failed: {e}")
        raise e

def run_ingestion():
    from agents.circuit_breaker import is_supabase_open
    if is_supabase_open():
        logger.error("Supabase circuit breaker is OPEN. Aborting run gracefully.")
        return
    asyncio.run(main_ingestion())

if __name__ == "__main__":
    run_ingestion()
