# Report 6: Ingestion Enhancements, Deduplication & RSS Enrichment

This report documents the developments, implementation choices, and testing results since Report 5, focusing on scraping optimization, query-based deduplication, and full-article RSS enrichment.

---

## 1. Scraper Optimization & Rewrite

### 1.1 HTTPX Scraper Optimization
- **Trafilatura Clean Text**: Configured `trafilatura` to extract clean markdown output, using `favor_recall=True` to prioritize extracting maximum content for LLM ingestion.
- **Per-Domain Throttling**: Implemented a per-domain async lock and rate-limiter, enforcing a minimum 1.0-second delay between requests to the same host to prevent IP bans.
- **429 & Retry-After Handling**: Added handling for HTTP 429 (Too Many Requests) to respect the server's `Retry-After` header when waiting.
- **Payload Capping**: Capped stored `raw_html` at 50,000 characters and skipped pages with less than 200 characters of clean content.

### 1.2 Playwright Scraper Optimization
- **Shared Browser Instance**: Re-engineered the Playwright scraper to accept a shared `Browser` instance passed from the orchestrator, eliminating Chromium startup overhead per source.
- **Resource Blocking**: Blocked heavy assets (images, fonts, stylesheets, and media) at the request interception level to significantly reduce network usage and execution time.
- **Selector & Fallback Support**: Added support for source-specific CSS query selectors (`scrape_config.item_selector`) for up to 30 items, falling back to full-page text extraction if no selector is defined.
- **Resilient Execution**: Configured a 30-second navigation timeout and 2-second JS settle time, alongside `--no-sandbox --disable-gpu` CLI flags for stability in headless environment runs.

---

## 2. Supabase Deduplication Strategy

To prevent redundant inserts and save database query cost, we implemented a pre-load deduplication strategy:
- **Set-Based Filtering**: At the start of the ingestion run, the orchestrator queries all known article URLs from the database:
  ```python
  known_urls = {r["url"] for r in db_res.data if r.get("url")}
  ```
- **Filter Step**: All scraped articles from all concurrent and sequential scraping routines are gathered and matched against this Python set in $O(1)$ time. Only brand new URLs proceed to the database insert phase.
- **Chunked Batch Insert**: The new items are inserted into Supabase in chunks of 500 utilizing the `upsert` mechanism with `on_conflict="url"` to prevent race conditions.

---

## 3. RSS Full-Article Enrichment

Because RSS feeds typically truncate content to short snippets (200–500 characters), which are insufficient for producing high-quality embeddings or performing reliable semantic deduplication, we added an enrichment step:
- **Shared Fetcher Utility**: Extracted the core HTTPX fetching logic to a reusable helper function `fetch_full_page`.
- **Concurrent In-Flight Fetching**: For all new RSS articles slated for insertion, we concurrently fetch their full-page HTML and extract clean markdown content.
- **arXiv Exception**: If the source URL points to `arxiv.org`, the paper's RSS feed already contains the complete abstract, which is sufficient for classification and deduplication. arXiv papers are therefore excluded from full-page fetching at this phase.
- **Fallback**: If fetching the full URL fails, the pipeline safely falls back to the feed's truncated summary to ensure no articles are lost.

---

## 4. Verification & Validation

An ingestion run was executed to verify the combined pipeline features:
- **Metrics**: 16 active sources were scraped. The scrapers returned a total of 177 articles.
- **Pre-Filtering**: The URLs were matched against the existing database items, filtering down to 111 new articles.
- **Enrichment**: The 111 new articles had their full content fetched and extracted concurrently via `fetch_full_page`.
- **Insertion**: All 111 enriched articles were successfully upserted into the `articles` database table in a single batch.
