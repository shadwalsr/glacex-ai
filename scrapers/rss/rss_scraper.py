import logging
import httpx
import feedparser
import sentry_sdk
from datetime import datetime, timezone
import time

logger = logging.getLogger(__name__)

async def scrape_rss(source: dict) -> list[dict]:
    """
    Scrapes an RSS feed source using feedparser and httpx.
    """
    try:
        last_scraped = source.get("last_scraped")
        from scrapers.httpx.httpx_scraper import to_http_date
        if_modified_since = to_http_date(last_scraped)
        headers = {"User-Agent": "GlaceX/1.0"}
        if if_modified_since:
            headers["If-Modified-Since"] = if_modified_since

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(source["url"], headers=headers, follow_redirects=True)
            if resp.status_code == 304:
                logger.info(f"RSS feed not modified (304) since {if_modified_since}: {source['url']}")
                return []
            resp.raise_for_status()

        # Parse the feed content using feedparser
        feed = feedparser.parse(resp.text)
        items = []
        for entry in feed.entries[:50]:  # cap at 50 per run
            # Convert published_parsed struct_time to datetime
            published_at = None
            struct_time = entry.get("published_parsed")
            if struct_time:
                try:
                    published_at = datetime(*struct_time[:6], tzinfo=timezone.utc).isoformat()
                except Exception:
                    published_at = None

            url = entry.get("link")
            title = entry.get("title")
            
            if not url or not title:
                continue

            items.append({
                "source_id": source["id"],
                "url": url.strip(),
                "title": title.strip(),
                "raw_html": entry.get("summary", "") or entry.get("description", ""),
                "clean_text": entry.get("summary", "") or entry.get("description", ""),
                "published_at": published_at,
                "status": "raw"
            })
        return items
    except Exception as e:
        logger.error(f"Error scraping RSS source {source.get('name') or source.get('id')}: {e}")
        sentry_sdk.capture_exception(e)
        return []
