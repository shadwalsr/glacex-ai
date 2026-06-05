-- Supabase Migration: 20260601000000_complete_normalized_schema.sql
-- Complete normalized schema for GlaceX.ai

-- 1. Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Drop existing tables if they exist to start fresh
DROP TABLE IF EXISTS failed_extractions, token_usage, pipeline_runs, article_entities, entities, insights, classifications, embeddings, raw_ingestion_log, articles, sources, pipeline_health, user_feedback CASCADE;

-- 3. Trigger function to auto-update updated_at column
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =========================================================================
-- TABLE 1: sources (registry)
-- =========================================================================
CREATE TABLE sources (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    url           TEXT NOT NULL UNIQUE,
    type          TEXT CHECK(type IN ('rss','playwright','httpx')),
    category      TEXT, -- 'newsletter','arxiv','twitter','hn','product'
    active        BOOLEAN DEFAULT true,
    last_scraped  TIMESTAMPTZ,
    scrape_config JSONB,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_sources_updated_at
BEFORE UPDATE ON sources
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- TABLE 2: raw_ingestion_log (audit)
-- =========================================================================
CREATE TABLE raw_ingestion_log (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id     UUID REFERENCES sources(id) ON DELETE CASCADE,
    status        TEXT NOT NULL, -- 'success', 'failed'
    items_scraped INT DEFAULT 0,
    error_message TEXT,
    duration_s    INT,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_raw_ingestion_log_updated_at
BEFORE UPDATE ON raw_ingestion_log
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- TABLE 3: articles (core store)
-- =========================================================================
CREATE TABLE articles (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id     UUID REFERENCES sources(id) ON DELETE SET NULL,
    url           TEXT NOT NULL UNIQUE,
    title         TEXT,
    raw_html      TEXT,
    clean_text    TEXT,
    published_at  TIMESTAMPTZ,
    scraped_at    TIMESTAMPTZ DEFAULT now(),
    status        TEXT DEFAULT 'raw', -- raw|embedded|escalated|filtered|analyzed|delivered
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_articles_updated_at
BEFORE UPDATE ON articles
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX idx_articles_status ON articles(status);
CREATE INDEX idx_articles_scraped_at ON articles(scraped_at DESC);

-- =========================================================================
-- TABLE 4: embeddings (vector store)
-- =========================================================================
CREATE TABLE embeddings (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id    UUID REFERENCES articles(id) ON DELETE CASCADE,
    chunk_index   INT DEFAULT 0,
    chunk_text    TEXT,
    embedding     vector(384),
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_embeddings_updated_at
BEFORE UPDATE ON embeddings
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =========================================================================
-- TABLE 5: classifications (Groq outputs)
-- =========================================================================
CREATE TABLE classifications (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id       UUID REFERENCES articles(id) ON DELETE CASCADE,
    category         TEXT, -- 'paper'|'tool'|'product'|'company'|'newsletter'
    subcategory      TEXT,
    importance       INT,
    is_ai_relevant   BOOLEAN,
    technical_depth  TEXT,
    reason           TEXT,
    raw_output       TEXT,
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_classifications_updated_at
BEFORE UPDATE ON classifications
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- TABLE 6: insights (Gemini outputs)
-- =========================================================================
CREATE TABLE insights (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id               UUID REFERENCES articles(id) ON DELETE CASCADE,
    headline                 TEXT NOT NULL,
    tldr                     TEXT[] NOT NULL,
    technical_depth          TEXT,
    practical_utility        TEXT,
    ecosystem_impact         TEXT,
    related_papers           TEXT[],
    related_entities         TEXT[],
    tags                     TEXT[],
    category                 TEXT,
    source_reliability_note  TEXT,
    created_at               TIMESTAMPTZ DEFAULT now(),
    updated_at               TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_insights_updated_at
BEFORE UPDATE ON insights
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- TABLE 7: entities (normalized NER registry)
-- =========================================================================
CREATE TABLE entities (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          TEXT NOT NULL,
    type          TEXT NOT NULL, -- 'ORG', 'PRODUCT', 'PERSON', 'GPE', etc.
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(name, type)
);

CREATE TRIGGER update_entities_updated_at
BEFORE UPDATE ON entities
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- TABLE 8: article_entities (junction table)
-- =========================================================================
CREATE TABLE article_entities (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id    UUID REFERENCES articles(id) ON DELETE CASCADE,
    entity_id     UUID REFERENCES entities(id) ON DELETE CASCADE,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now(),
    UNIQUE(article_id, entity_id)
);

CREATE TRIGGER update_article_entities_updated_at
BEFORE UPDATE ON article_entities
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- TABLE 9: pipeline_runs (statistics)
-- =========================================================================
CREATE TABLE pipeline_runs (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at        TIMESTAMPTZ DEFAULT now(),
    ingested      INT DEFAULT 0,
    embedded      INT DEFAULT 0,
    duplicates    INT DEFAULT 0,
    new_signals   INT DEFAULT 0,
    analyzed      INT DEFAULT 0,
    delivered     INT DEFAULT 0,
    errors        JSONB,
    duration_s    INT DEFAULT 0,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_pipeline_runs_updated_at
BEFORE UPDATE ON pipeline_runs
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- TABLE 10: token_usage (budget tracking)
-- =========================================================================
CREATE TABLE token_usage (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        UUID, -- links to run or session
    model         TEXT NOT NULL,
    input_tokens  INT DEFAULT 0,
    output_tokens INT DEFAULT 0,
    cost_usd      NUMERIC(10, 6) DEFAULT 0.000000,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_token_usage_updated_at
BEFORE UPDATE ON token_usage
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- TABLE 11: failed_extractions (debug logs)
-- =========================================================================
CREATE TABLE failed_extractions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id        UUID REFERENCES articles(id) ON DELETE CASCADE,
    model         TEXT NOT NULL,
    raw_output    TEXT,
    error         TEXT,
    run_id        UUID,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);

CREATE TRIGGER update_failed_extractions_updated_at
BEFORE UPDATE ON failed_extractions
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =========================================================================
-- Row Level Security (RLS) Enablement
-- =========================================================================
ALTER TABLE sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE raw_ingestion_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE classifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE insights ENABLE ROW LEVEL SECURITY;
ALTER TABLE entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE article_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE token_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE failed_extractions ENABLE ROW LEVEL SECURITY;

-- =========================================================================
-- Vector Similarity matching RPC function
-- =========================================================================
CREATE OR REPLACE FUNCTION match_embeddings(
  query_embedding vector(384),
  match_threshold float DEFAULT 0.85,
  match_count int DEFAULT 5
)
RETURNS TABLE(article_id UUID, similarity float) AS $$
  SELECT e.article_id,
         1 - (e.embedding <=> query_embedding) AS similarity
  FROM embeddings e
  JOIN articles a ON a.id = e.article_id
  WHERE e.chunk_index = 0
    AND a.status != 'raw'   -- only compare against existing archive
    AND a.scraped_at > NOW() - INTERVAL '30 days'  -- recent only
    AND 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
$$ LANGUAGE sql STABLE;
