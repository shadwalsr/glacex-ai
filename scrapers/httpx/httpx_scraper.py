import asyncio
import logging
import time
from urllib.parse import urlparse

import httpx
import trafilatura
import sentry_sdk

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Per-domain rate limiter
# Tracks last-hit timestamps per domain and enforces a 1-second delay between
# requests to the same domain to avoid IP bans.
# ---------------------------------------------------------------------------
_domain_last_hit: dict[str, float] = {}
_domain_lock: dict[str, asyncio.Lock] = {}
_global_lock = asyncio.Lock()

async def _get_domain_lock(domain: str) -> asyncio.Lock:
    """Return (and lazily create) an asyncio.Lock for this domain."""
    async with _global_lock:
        if domain not in _domain_lock:
            _domain_lock[domain] = asyncio.Lock()
        return _domain_lock[domain]

async def _domain_throttle(domain: str, min_gap: float = 1.0) -> None:
    """
    Enforces a minimum inter-request gap of `min_gap` seconds per domain.
    Serialises concurrent requests to the same domain through a per-domain lock.
    """
    lock = await _get_domain_lock(domain)
    async with lock:
        now = time.monotonic()
        last = _domain_last_hit.get(domain, 0.0)
        wait = min_gap - (now - last)
        if wait > 0:
            logger.debug(f"Rate-limit: sleeping {wait:.2f}s before hitting {domain}")
            await asyncio.sleep(wait)
        _domain_last_hit[domain] = time.monotonic()

async def fetch_full_page(url: str, if_modified_since: str = None) -> tuple[str | None, str | None]:
    """
    Fetches a page, respects rate-limits/Retry-After, and extracts clean markdown.
    Returns (clean_text, raw_html) or (None, None) on failure.
    """
    try:
        domain = urlparse(url).netloc
        # Enforce rate limit before opening the connection
        await _domain_throttle(domain)

        headers = {"User-Agent": "Mozilla/5.0 GlaceX/1.0"}
        if if_modified_since:
            headers["If-Modified-Since"] = if_modified_since

        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers=headers,
        ) as client:
            resp = await client.get(url)

            # Handle 304 Not Modified
            if resp.status_code == 304:
                logger.info(f"Page not modified (304) since {if_modified_since}: {url}")
                return None, None

            # Handle 429 Too Many Requests — honour Retry-After
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 60))
                logger.warning(
                    f"[429] {url} asked us to back off for {retry_after:.0f}s — waiting then skipping."
                )
                await asyncio.sleep(retry_after)
                return None, None

            resp.raise_for_status()

        # Trafilatura: extract main article text, strip nav/ads
        clean = trafilatura.extract(
            resp.text,
            include_comments=False,
            include_tables=True,
            favor_recall=True,          # prefer more text over precision
            output_format="markdown",   # get markdown for LLM consumption
        )

        if not clean or len(clean) < 200:
            logger.info(f"Page content too short (< 200 chars), probably not an article: {url}")
            return None, None

        return clean, resp.text[:50_000]

    except Exception as e:
        logger.error(f"Error fetching full page {url}: {e}")
        sentry_sdk.capture_exception(e)
        return None, None

def to_http_date(dt_str):
    if not dt_str:
        return None
    try:
        from datetime import datetime
        import email.utils
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return email.utils.format_datetime(dt)
    except Exception:
        return None

async def scrape_httpx(source: dict) -> list[dict]:
    """
    Scrapes a static web page, extracts clean markdown content via trafilatura.

    Resilience rules:
    - Per-domain throttle: 1.0 s minimum gap between requests to same host.
    - Respects Retry-After header if the server returns a 429.
    - On any failure: logs to Sentry, returns empty list (never raises).
    """
    url = source["url"]
    name = source.get("name", url)
    last_scraped = source.get("last_scraped")
    if_modified_since = to_http_date(last_scraped)

    clean, raw_html = await fetch_full_page(url, if_modified_since)
    if not clean:
        return []

    return [{
        "source_id": source["id"],
        "url": url,
        "title": name,
        "raw_html": raw_html,
        "clean_text": clean,
        "published_at": None,
        "status": "raw",
    }]
