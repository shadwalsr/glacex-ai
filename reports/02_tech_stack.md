# Report 2: GlaceX.ai Technical Stack Architecture

## Overview
GlaceX.ai is built using a **$0 Budget Optimized** stack. It leverages high-value, zero-cost developer tiers and employs a Serverless Batch Architecture. This ensures that the entire pipeline runs on a scheduled automation loop, eliminating always-on hosting fees.

## Core Technologies

### 1. Orchestration & Agents
- **Language:** Python 3.11
- **Framework:** LangChain
- **Purpose:** Powers the document loaders, manages RAG chains, and orchestrates the EnsembleRetriever framework.

### 2. Inference Engine (Dual-LLM Pipeline)
- **Groq API (Llama 3.3):** Used for fast classification and initial duplicate checks.
- **Gemini 2.0 Flash:** Leveraged for its massive 1M token context window, used for full paper extraction and generating deep technical summaries.

### 3. Data Scraping
- **Tools:** Playwright, HTTPX, and Trafilatura.
- **Purpose:** Bypasses API call limits and pulls clean text/markdown from raw HTML and RSS feeds entirely for free.

### 4. Database & Storage
- **Relational Storage:** Supabase (PostgreSQL) for raw HTML logs, source configurations, relational metadata, and article archiving.
- **Vector Engine:** Supabase (`pgvector`) runs direct vector similarity calculations inside PostgreSQL, avoiding the need for an external vector host.

### 5. Local NLP & Embeddings
- **Embeddings:** Hugging Face `sentence-transformers` (`bge-small-en-v1.5`) runs locally on CPU.
- **NER:** `spaCy` handles ultra-fast local Named Entity Recognition.

### 6. Hybrid Search
- **Tool:** `rank_bm25`
- **Purpose:** Works alongside `pgvector` via Reciprocal Rank Fusion (RRF) to provide pinpoint keyword and semantic searches.

### 7. Automation & Delivery
- **Cron Serverless Worker:** GitHub Actions triggers the Python pipeline every 6 hours ($0 cost with 2,000 free minutes/mo).
- **Delivery:** `ntfy.sh` sends real-time, curated briefings directly to mobile devices via zero-auth HTTP POST requests.

### 8. Observability
- **LangSmith:** Visual tracking of LLM inputs, outputs, and agent steps.
- **Sentry:** Monitors system-level infrastructure and catches scraping crashes.

## Environment Management
- **Dependency Manager:** `uv`
- **Lockfile:** Strict, exact version pinning in `pyproject.toml` (e.g., LangChain 0.3.x, Playwright 1.45.x) to ensure reproducible builds on GitHub Actions.
