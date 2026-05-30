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

    try:
        domain = urlparse(url).netloc
        # Enforce rate limit before opening the connection
        await _domain_throttle(domain)

        async with httpx.AsyncClient(
            timeout=20,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 GlaceX/1.0"},
        ) as client:
            resp = await client.get(url)

            # Handle 429 Too Many Requests — honour Retry-After
            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", 60))
                logger.warning(
                    f"[429] {name} asked us to back off for {retry_after:.0f}s — waiting then skipping this run."
                )
                await asyncio.sleep(retry_after)
                return []

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
            logger.info(f"Skipping {name} — extracted text too short (< 200 chars), probably not an article.")
            return []

        return [{
            "source_id": source["id"],
            "url": url,
            "title": name,
            "raw_html": resp.text[:50_000],  # cap raw HTML storage at 50k chars
            "clean_text": clean,
            "published_at": None,
            "status": "raw",
        }]

    except Exception as e:
        logger.error(f"Error scraping HTTPX source {name}: {e}")
        sentry_sdk.capture_exception(e)
        return []
