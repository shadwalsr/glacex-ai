import logging
import httpx
import trafilatura

logger = logging.getLogger(__name__)

async def scrape_httpx(source, client: httpx.AsyncClient):
    """
    Scrapes a static web page source using HTTPX and extracts clean text using trafilatura.
    """
    url = source["url"]
    name = source["name"]
    logger.info(f"Starting HTTPX scrape for {name} ({url})")

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = await client.get(url, headers=headers, follow_redirects=True, timeout=30.0)
        
        if response.status_code != 200:
            logger.error(f"Failed to fetch {name} ({url}): HTTP {response.status_code}")
            return []

        # Extract text content
        html_content = response.text
        clean_text = trafilatura.extract(html_content)
        
        # If extraction is empty or None, fallback to simple title or content
        if not clean_text:
            clean_text = ""

        # For static HTTPX scraping, the source URL itself is typically the target article.
        # We wrap this in a single article item.
        return [{
            "title": name,
            "url": url,
            "raw_html": html_content,
            "clean_text": clean_text,
            "published_at": None
        }]
    except Exception as e:
        logger.error(f"Error scraping HTTPX source {name}: {e}")
        return []
