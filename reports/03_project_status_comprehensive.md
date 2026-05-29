# Report 3: Comprehensive Project Status & Architecture

## 1. Project Overview
**GlaceX.ai** is an autonomous, multi-agent curation engine. It replaces the manual tracking of dozens of AI newsletters, arXiv papers, and product launches with an automated background pipeline. It extracts raw architectural advancements, maps startup ecosystems, and cross-references data to eliminate redundant media noise.

## 2. Technical Stack ($0 Budget Optimized)
The entire stack is built to leverage high-value free tiers:
- **Orchestration:** Python 3.11 with `uv` for ultra-fast, strict lockfile dependency management.
- **Agents:** LangChain framework structure.
- **Inference Pipeline:** Groq (Llama 3.3) for fast deduplication/classification, and Gemini 2.0 Flash for deep, massive-context extraction.
- **Database & Storage:** Supabase (PostgreSQL) for relational data and `pgvector` for on-board vector embeddings.
- **NLP & Search:** HuggingFace `sentence-transformers` (`bge-small-en-v1.5`), `spaCy` for NER, and `rank_bm25` for hybrid search.
- **Scraping:** Playwright, HTTPX, and Trafilatura.
- **Automation & CI:** GitHub Actions (Cron triggers).
- **Delivery:** `ntfy.sh` for push notifications.

## 3. Database Architecture (Supabase)
We successfully injected the exact schema into Supabase and explicitly **disabled Row Level Security (RLS)** across all tables to allow our service role key seamless access.

The tables include:
1. `sources`: Manages target URLs (rss, playwright, httpx), categories, and scrape configurations.
2. `articles`: The raw data lake holding HTML, clean text, and scraping metadata. (Includes indexes on `status`, `scraped_at`, and `url`).
3. `embeddings`: Utilizing `pgvector(384)` with an `ivfflat` index for semantic search.
4. `intelligence`: Curated final outputs containing LLM summaries, key signals, and an importance score (1-10).
5. `deliveries`: An idempotency log tracking what has been sent to the user via `ntfy.sh`.

## 4. Pipeline Configuration
The system runs via GitHub Actions (`.github/workflows/pipeline.yml`) triggered every 6 hours. 
Key design decisions in the pipeline:
- **Fail-Fast Validation:** A custom `scripts/validate_env.py` script runs immediately to verify that all 7 required secrets (`SUPABASE_URL`, `GROQ_API_KEY`, etc.) exist before launching heavy jobs.
- **Caching:** HuggingFace models (`~/.cache/huggingface`) and Python dependencies are cached across runs to save ~3 minutes per run.
- **Timeout Protection:** A strict `timeout-minutes: 50` is enforced to prevent runaway jobs from eating the 2,000 monthly free tier minutes.
- **5-Phase Modularity:**
  - Phase 1: Ingest
  - Phase 2: Embed & NER
  - Phase 3: Deduplicate
  - Phase 4: LLM Analysis
  - Phase 5: Store & Deliver

## 5. Seeded Data
A `sources.yaml` file was created and ingested into the database via `scripts/seed_sources.py`. We seeded exactly **16 critical sources** to keep the pipeline well under the 50-minute timeout:
- **Newsletters:** The Batch, TLDR AI, Import AI, The Rundown AI
- **Research:** arXiv cs.AI, cs.LG, cs.CL
- **Company Blogs:** OpenAI, Anthropic, Google DeepMind, Mistral AI, Cohere
- **Aggregators & Investors:** Hugging Face Blog, AI News, TechCrunch AI, VentureBeat AI

## 6. Development Environment Setup
- The project structure (`agents/`, `scrapers/`, `db/`, `nlp/`, `llm/`, `delivery/`) is fully scaffolded.
- `pyproject.toml` is configured with strict package targeting for `hatchling`.
- A git-ignored `.env.local` pattern is established for local development.

**Status:** The infrastructure, database, CI/CD pipeline, and source targets are 100% complete and deployed. The system is now ready for the core Python Agent development (starting with Phase 1: Ingest).
