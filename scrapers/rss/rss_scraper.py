import xml.etree.ElementTree as ET
import logging
from datetime import datetime
import httpx

logger = logging.getLogger(__name__)

def parse_rss_xml(xml_content):
    """
    Parses RSS/Atom/RDF feeds in a namespace-agnostic manner.
    Returns a list of dicts: [{'title': ..., 'url': ..., 'published_at': ...}]
    """
    try:
        root = ET.fromstring(xml_content)
    except Exception as e:
        logger.error(f"Failed to parse XML: {e}")
        return []

    articles = []
    
    # Locate all items or entries
    items = []
    for elem in root.iter():
        tag_lower = elem.tag.lower()
        if tag_lower.endswith('item') or tag_lower.endswith('entry'):
            items.append(elem)

    for item in items:
        title = None
        url = None
        published_at_str = None
        
        for child in item:
            tag_name = child.tag.lower().split('}')[-1]
            if tag_name == 'title':
                title = child.text
            elif tag_name == 'link':
                # Atom links can be in href attribute
                if child.attrib.get('href'):
                    url = child.attrib.get('href')
                else:
                    url = child.text
            elif tag_name in ['pubdate', 'published', 'updated', 'date']:
                published_at_str = child.text

        # Standard cleanups
        if title:
            title = title.strip()
        if url:
            url = url.strip()

        # Parse date if available
        published_at = None
        if published_at_str:
            try:
                # Basic attempts to parse ISO/RFC2822 dates
                # In python 3.11+, fromisoformat supports Z and offsets
                published_at_str = published_at_str.strip()
                # Remove timezone names like EST/GMT if present to avoid parser failure
                # Simple replacement for common formats:
                if "," in published_at_str: # RFC 2822 (e.g. "Mon, 02 Jun 2016 02:23:45 MST")
                    # Try built-in parsing or standard fallback
                    # We can use email.utils.parsedate_to_datetime
                    import email.utils
                    published_at = email.utils.parsedate_to_datetime(published_at_str)
                else:
                    # Try fromisoformat (handles 'Z' and '+00:00')
                    # Replace Z with +00:00 for older python compatibility if needed, but 3.11+ handles it.
                    published_at = datetime.fromisoformat(published_at_str)
            except Exception:
                published_at = None

        if url and title:
            articles.append({
                "title": title,
                "url": url,
                "published_at": published_at
            })
            
    return articles

async def scrape_rss(source, client: httpx.AsyncClient):
    """
    Scrapes an RSS feed source.
    """
    url = source["url"]
    name = source["name"]
    logger.info(f"Starting RSS scrape for {name} ({url})")
    
    try:
        response = await client.get(url, follow_redirects=True, timeout=30.0)
        if response.status_code != 200:
            logger.error(f"Failed to fetch RSS feed {name} ({url}): HTTP {response.status_code}")
            return []
            
        articles = parse_rss_xml(response.content)
        logger.info(f"Successfully scraped {len(articles)} articles from {name}")
        return articles
    except Exception as e:
        logger.error(f"Error scraping RSS source {name}: {e}")
        return []
