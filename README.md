# Glacex.ai - Autonomous Intelligence for the Technical Mind

Glacex.ai is a state-of-the-art autonomous intelligence pipeline and dashboard engineered specifically for researchers, developers, and technical leaders in the artificial intelligence sector. 

In a landscape flooded with daily AI announcements, product launches, and academic papers, finding genuinely impactful technical information is overwhelming. Glacex.ai solves this by acting as an autonomous technical researcher. The platform continuously aggregates, analyzes, and ranks artificial intelligence news, research papers, and engineering blogs, filtering out marketing noise and delivering only high-value, actionable signals.

## Architecture & How It Works

Glacex.ai is composed of a robust Python backend and a modern React frontend.

### 1. Data Ingestion
The **Ingestion Agent** continually scrapes unstructured data from high-signal configured sources (RSS feeds, arXiv, elite engineering blogs like OpenAI, DeepMind, Meta, and newsletters). It hands this data to the **NLP & Deduplication Agents** which use natural language processing and semantic embeddings to detect and drop redundant articles.

### 2. Autonomous LLM Evaluation
Unique articles are passed to the **LLM Agent**, which leverages powerful models (Groq/Gemini) to perform deep semantic analysis.
* **Classification & Scoring:** Evaluates technical depth, categorization, and assigns an **Importance Score** (0-100).
* **Entity Extraction:** Identifies key models, frameworks, concepts, and companies.
* **Insight Generation:** Writes a dense, objective, structured summary explaining the technical impact.

### 3. Real-time Dashboard
The frontend is a highly responsive "glassmorphism" React dashboard built with Vite and Tailwind CSS.
* **The Feed:** Renders ranked articles based on their Importance Score and AI relevancy.
* **Detail Drawer:** Interactive slider providing the LLM's full classification reasoning and the complete article text.
* **Saved Signals:** A persistent bookmarking system tied to the Supabase database.
* **Architecture Health:** Real-time visualization of scraping pipeline health, API latencies, and circuit breakers.

## Tech Stack
* **Backend:** Python, Supabase (PostgreSQL), Groq API, Google Gemini API.
* **Frontend:** React, React Router, Vite, Tailwind CSS.
* **CI/CD:** GitHub Actions for automated deployment to GitHub Pages.

## Directory Structure
* `/agents/` - Python scripts for the core autonomous agents (Ingestion, NLP, LLM, Dedup).
* `/backend/` - Configuration, Prompts, and execution logic.
* `/dashboard/` - React frontend source code.
* `/supabase/` - Database schemas and migrations.
* `/scripts/` - Maintenance and utility scripts.

## Setup & Running Locally

### Dashboard
```bash
cd dashboard
npm install
npm run dev
```

### Backend Services
Ensure you have the required API keys (Supabase, Groq, Gemini) configured in `.env.local`.
```bash
uv run python scripts/seed_sources.py
uv run python agents/ingestion_agent.py
```

## Sitemap
* `/` - Home (Latest Previews & Spotlight)
* `/feed` - The main intelligence feed
* `/saved` - Saved high-value signals
* `/health` - System Architecture and Pipeline Health
* `/terminal` - Interactive Research Terminal
* `/sources` - Monitored data sources
* `/about` - About Glacex.ai & Sitemap
