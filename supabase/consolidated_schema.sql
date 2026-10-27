-- ==========================================
-- Migration: 20260601000000_complete_normalized_schema.sql
-- ==========================================
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


-- ==========================================
-- Migration: 20260601000001_add_upsert_and_transactional_rpc.sql
-- ==========================================
-- Supabase Migration: 20260601000001_add_upsert_and_transactional_rpc.sql

-- 1. Alter articles table to support text_hash and fetch_count metadata
ALTER TABLE articles ADD COLUMN IF NOT EXISTS text_hash TEXT UNIQUE;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE articles ADD COLUMN IF NOT EXISTS fetch_count INT DEFAULT 1;
ALTER TABLE articles ADD COLUMN IF NOT EXISTS embedding vector(384);

-- 2. Ensure classifications and insights have unique constraints on article_id for idempotency
ALTER TABLE classifications DROP CONSTRAINT IF EXISTS classifications_article_id_key;
ALTER TABLE classifications ADD CONSTRAINT classifications_article_id_key UNIQUE(article_id);

ALTER TABLE insights DROP CONSTRAINT IF EXISTS insights_article_id_key;
ALTER TABLE insights ADD CONSTRAINT insights_article_id_key UNIQUE(article_id);

-- 3. Trigger to copy chunk_index = 0 embedding directly into articles.embedding
CREATE OR REPLACE FUNCTION update_article_lead_embedding()
RETURNS TRIGGER AS $$
BEGIN
  IF NEW.chunk_index = 0 THEN
    UPDATE articles
    SET embedding = NEW.embedding,
        updated_at = NOW()
    WHERE id = NEW.article_id;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_update_article_lead_embedding ON embeddings;
CREATE TRIGGER trigger_update_article_lead_embedding
AFTER INSERT OR UPDATE ON embeddings
FOR EACH ROW EXECUTE FUNCTION update_article_lead_embedding();

-- 4. Supabase RPC for bulk upsert of raw articles
CREATE OR REPLACE FUNCTION bulk_upsert_articles(p_articles JSONB)
RETURNS VOID AS $$
DECLARE
  elem JSONB;
BEGIN
  FOR elem IN SELECT * FROM jsonb_array_elements(p_articles) LOOP
    -- Try updating by URL first
    UPDATE articles
    SET last_seen_at = NOW(),
        fetch_count = articles.fetch_count + 1
    WHERE url = elem->>'url';
    
    IF NOT FOUND THEN
      -- Try updating by text_hash next
      UPDATE articles
      SET last_seen_at = NOW(),
          fetch_count = articles.fetch_count + 1
      WHERE text_hash = elem->>'text_hash';
      
      IF NOT FOUND THEN
        -- Insert new article
        BEGIN
          INSERT INTO articles (
            source_id, url, title, raw_html, clean_text, published_at, status, text_hash, last_seen_at, fetch_count
          ) VALUES (
            (elem->>'source_id')::UUID,
            elem->>'url',
            elem->>'title',
            elem->>'raw_html',
            elem->>'clean_text',
            (elem->>'published_at')::TIMESTAMPTZ,
            COALESCE(elem->>'status', 'raw'),
            elem->>'text_hash',
            NOW(),
            1
          );
        EXCEPTION WHEN unique_violation THEN
          -- Fallback/ignore if something concurrently inserted it
          NULL;
        END;
      END IF;
    END IF;
  END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 5. Supabase RPC for atomic transactional insert/update of Article + Classification + Insight
CREATE OR REPLACE FUNCTION upsert_full_article_pipeline_data(
  p_article_url TEXT,
  p_article_title TEXT,
  p_article_raw_html TEXT,
  p_article_clean_text TEXT,
  p_article_published_at TIMESTAMPTZ,
  p_article_status TEXT,
  p_article_text_hash TEXT,
  p_source_id UUID,
  
  -- Classification fields
  p_class_category TEXT DEFAULT NULL,
  p_class_subcategory TEXT DEFAULT NULL,
  p_class_importance INT DEFAULT NULL,
  p_class_is_ai_relevant BOOLEAN DEFAULT NULL,
  p_class_technical_depth TEXT DEFAULT NULL,
  p_class_reason TEXT DEFAULT NULL,
  
  -- Insight fields
  p_insight_headline TEXT DEFAULT NULL,
  p_insight_tldr TEXT[] DEFAULT NULL,
  p_insight_technical_depth TEXT DEFAULT NULL,
  p_insight_practical_utility TEXT DEFAULT NULL,
  p_insight_ecosystem_impact TEXT DEFAULT NULL,
  p_insight_related_papers TEXT[] DEFAULT NULL,
  p_insight_related_entities TEXT[] DEFAULT NULL,
  p_insight_tags TEXT[] DEFAULT NULL,
  p_insight_source_reliability_note TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
  v_article_id UUID;
BEGIN
  -- A. Try updating core article by URL first
  UPDATE articles
  SET last_seen_at = NOW(),
      fetch_count = articles.fetch_count + 1
  WHERE url = p_article_url
  RETURNING id INTO v_article_id;
  
  IF v_article_id IS NULL THEN
    -- Try updating by text_hash next
    UPDATE articles
    SET last_seen_at = NOW(),
        fetch_count = articles.fetch_count + 1
    WHERE text_hash = p_article_text_hash
    RETURNING id INTO v_article_id;
    
    IF v_article_id IS NULL THEN
      -- Insert new article
      BEGIN
        INSERT INTO articles (
          url, title, raw_html, clean_text, published_at, status, text_hash, source_id, last_seen_at, fetch_count
        ) VALUES (
          p_article_url, p_article_title, p_article_raw_html, p_article_clean_text, p_article_published_at, p_article_status, p_article_text_hash, p_source_id, NOW(), 1
        )
        RETURNING id INTO v_article_id;
      EXCEPTION WHEN unique_violation THEN
        -- If concurrent insert happened, fetch the ID
        SELECT id INTO v_article_id FROM articles WHERE url = p_article_url;
        IF v_article_id IS NULL THEN
          SELECT id INTO v_article_id FROM articles WHERE text_hash = p_article_text_hash;
        END IF;
      END;
    END IF;
  END IF;
  
  -- B. Upsert classification if category was provided
  IF p_class_category IS NOT NULL THEN
    INSERT INTO classifications (
      article_id, category, subcategory, importance, is_ai_relevant, technical_depth, reason
    ) VALUES (
      v_article_id, p_class_category, p_class_subcategory, p_class_importance, p_class_is_ai_relevant, p_class_technical_depth, p_class_reason
    )
    ON CONFLICT (article_id) DO UPDATE SET
      category = EXCLUDED.category,
      subcategory = EXCLUDED.subcategory,
      importance = EXCLUDED.importance,
      is_ai_relevant = EXCLUDED.is_ai_relevant,
      technical_depth = EXCLUDED.technical_depth,
      reason = EXCLUDED.reason,
      updated_at = NOW();
  END IF;
  
  -- C. Upsert insight if headline was provided
  IF p_insight_headline IS NOT NULL THEN
    INSERT INTO insights (
      article_id, headline, tldr, technical_depth, practical_utility, ecosystem_impact, related_papers, related_entities, tags, category, source_reliability_note
    ) VALUES (
      v_article_id, p_insight_headline, p_insight_tldr, p_insight_technical_depth, p_insight_practical_utility, p_insight_ecosystem_impact, p_insight_related_papers, p_insight_related_entities, p_insight_tags, COALESCE(p_class_category, 'other'), p_insight_source_reliability_note
    )
    ON CONFLICT (article_id) DO UPDATE SET
      headline = EXCLUDED.headline,
      tldr = EXCLUDED.tldr,
      technical_depth = EXCLUDED.technical_depth,
      practical_utility = EXCLUDED.practical_utility,
      ecosystem_impact = EXCLUDED.ecosystem_impact,
      related_papers = EXCLUDED.related_papers,
      related_entities = EXCLUDED.related_entities,
      tags = EXCLUDED.tags,
      category = EXCLUDED.category,
      source_reliability_note = EXCLUDED.source_reliability_note,
      updated_at = NOW();
  END IF;
  
  RETURN v_article_id;
END;
$$ LANGUAGE plpgsql;


-- ==========================================
-- Migration: 20260601000002_add_match_documents_rpc.sql
-- ==========================================
-- Supabase Migration: 20260601000002_add_match_documents_rpc.sql
-- Create standard match_documents function for LangChain SupabaseVectorStore

CREATE OR REPLACE FUNCTION match_documents(
  query_embedding vector(384),
  match_threshold float,
  match_count int,
  filter jsonb default '{}'
)
RETURNS TABLE (
  id UUID,
  content TEXT,
  metadata JSONB,
  similarity FLOAT
) AS $$
BEGIN
  RETURN QUERY
  SELECT
    e.id,
    e.chunk_text AS content,
    jsonb_build_object(
      'article_id', a.id,
      'title', a.title,
      'url', a.url,
      'source_id', a.source_id,
      'published_at', a.published_at,
      'category', a.status
    ) AS metadata,
    1 - (e.embedding <=> query_embedding) AS similarity
  FROM embeddings e
  JOIN articles a ON a.id = e.article_id
  WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$ LANGUAGE plpgsql STABLE;


-- ==========================================
-- Migration: 20260601000003_add_deliveries_table.sql
-- ==========================================
-- Supabase Migration: 20260601000003_add_deliveries_table.sql
-- Create deliveries table to track pushed alerts and digests

CREATE TABLE IF NOT EXISTS deliveries (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  insight_id      UUID REFERENCES insights(id) ON DELETE CASCADE,
  channel         TEXT NOT NULL, -- 'ntfy'
  delivered_at    TIMESTAMPTZ DEFAULT now(),
  payload         JSONB,
  created_at      TIMESTAMPTZ DEFAULT now(),
  updated_at      TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS update_deliveries_updated_at ON deliveries;
CREATE TRIGGER update_deliveries_updated_at
BEFORE UPDATE ON deliveries
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE deliveries ENABLE ROW LEVEL SECURITY;


-- ==========================================
-- Migration: 20260601000004_add_pipeline_health_table.sql
-- ==========================================
-- Supabase Migration: 20260601000004_add_pipeline_health_table.sql
-- Create pipeline_health table to track per-run health score metrics

CREATE TABLE IF NOT EXISTS pipeline_health (
  id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id               UUID REFERENCES pipeline_runs(id) ON DELETE CASCADE,
  sources_successful   INT DEFAULT 0,
  sources_total        INT DEFAULT 0,
  new_signals          INT DEFAULT 0,
  expected_new_signals INT DEFAULT 5,
  llm_success_rate     DOUBLE PRECISION DEFAULT 1.0,
  health_score         DOUBLE PRECISION NOT NULL,
  created_at           TIMESTAMPTZ DEFAULT now(),
  updated_at           TIMESTAMPTZ DEFAULT now()
);

-- Ensure foreign key constraint exists even if table existed before
ALTER TABLE public.pipeline_health
  DROP CONSTRAINT IF EXISTS fk_pipeline_health_run;
ALTER TABLE public.pipeline_health
  ADD CONSTRAINT fk_pipeline_health_run FOREIGN KEY (run_id) REFERENCES public.pipeline_runs(id) ON DELETE CASCADE;

DROP TRIGGER IF EXISTS update_pipeline_health_updated_at ON pipeline_health;
CREATE TRIGGER update_pipeline_health_updated_at
BEFORE UPDATE ON pipeline_health
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE pipeline_health ENABLE ROW LEVEL SECURITY;

-- Add a public select policy for the read-only dashboard
DROP POLICY IF EXISTS "Allow public read-only access to pipeline_health" ON pipeline_health;
CREATE POLICY "Allow public read-only access to pipeline_health" ON pipeline_health
  FOR SELECT USING (true);


-- ==========================================
-- Migration: 20260601000005_add_pipeline_runs_public_policy.sql
-- ==========================================
-- Supabase Migration: 20260601000005_add_pipeline_runs_public_policy.sql
-- Add a public SELECT policy for the read-only health dashboard to access pipeline_runs

DROP POLICY IF EXISTS "Allow public read-only access to pipeline_runs" ON pipeline_runs;
CREATE POLICY "Allow public read-only access to pipeline_runs" ON pipeline_runs
  FOR SELECT USING (true);


-- ==========================================
-- Migration: 20260601000006_add_circuit_breakers.sql
-- ==========================================
-- Supabase Migration: 20260601000006_add_circuit_breakers.sql
-- Create circuit_breaker_state table to track external service health across runs

CREATE TABLE IF NOT EXISTS circuit_breaker_state (
  service_name     TEXT PRIMARY KEY,
  state            TEXT NOT NULL CHECK (state IN ('closed', 'open', 'half-open')),
  failure_count    INT DEFAULT 0,
  last_failure_at  TIMESTAMPTZ,
  reset_at         TIMESTAMPTZ,
  created_at       TIMESTAMPTZ DEFAULT now(),
  updated_at       TIMESTAMPTZ DEFAULT now()
);

DROP TRIGGER IF EXISTS update_circuit_breaker_state_updated_at ON circuit_breaker_state;
CREATE TRIGGER update_circuit_breaker_state_updated_at
BEFORE UPDATE ON circuit_breaker_state
FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable RLS
ALTER TABLE circuit_breaker_state ENABLE ROW LEVEL SECURITY;

-- Allow service role to perform all actions
DROP POLICY IF EXISTS "Allow service role all on circuit_breaker_state" ON circuit_breaker_state;
CREATE POLICY "Allow service role all on circuit_breaker_state" ON circuit_breaker_state
  USING (true) WITH CHECK (true);


-- ==========================================
-- Migration: 20260601000007_add_run_checkpoints.sql
-- ==========================================
CREATE TABLE IF NOT EXISTS public.run_checkpoints (
    run_id UUID NOT NULL,
    phase TEXT NOT NULL,
    phase_started_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,
    phase_completed_at TIMESTAMP WITH TIME ZONE,
    docs_processed INTEGER DEFAULT 0 NOT NULL,
    PRIMARY KEY (run_id, phase)
);

ALTER TABLE public.run_checkpoints ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow service_role full access to run_checkpoints" ON public.run_checkpoints;
CREATE POLICY "Allow service_role full access to run_checkpoints"
    ON public.run_checkpoints
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


-- ==========================================
-- Migration: 20260601000008_add_user_feedback.sql
-- ==========================================
-- Migration: add user_feedback table for signal quality feedback loop
-- Triggered by ntfy.sh action buttons → GitHub Actions webhook → this table.

CREATE TABLE IF NOT EXISTS public.user_feedback (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID NOT NULL REFERENCES public.articles(id) ON DELETE CASCADE,
    rating     TEXT NOT NULL CHECK (rating IN ('good', 'noise')),
    rated_at   TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL,

    -- One feedback rating per article (idempotent upserts; last-writer-wins)
    CONSTRAINT user_feedback_article_id_unique UNIQUE (article_id)
);

-- Ensure unique constraint and foreign key constraint exist even if table existed before
ALTER TABLE public.user_feedback
  DROP CONSTRAINT IF EXISTS fk_user_feedback_article,
  DROP CONSTRAINT IF EXISTS user_feedback_article_id_unique;

ALTER TABLE public.user_feedback
  ADD CONSTRAINT fk_user_feedback_article FOREIGN KEY (article_id) REFERENCES public.articles(id) ON DELETE CASCADE,
  ADD CONSTRAINT user_feedback_article_id_unique UNIQUE (article_id);

CREATE INDEX IF NOT EXISTS idx_user_feedback_rated_at ON public.user_feedback (rated_at);
CREATE INDEX IF NOT EXISTS idx_user_feedback_rating   ON public.user_feedback (rating);

ALTER TABLE public.user_feedback ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow service_role full access to user_feedback" ON public.user_feedback;
CREATE POLICY "Allow service_role full access to user_feedback"
    ON public.user_feedback
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);


-- ==========================================
-- Migration: 20260601000009_add_classification_accuracy.sql
-- ==========================================
-- Migration: add classification_accuracy column to pipeline_runs
-- Tracks the fraction of classifications within ±15 points of human-verified labels.
-- Populated by delivery_agent.py after each run via update_pipeline_run_metric().

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS classification_accuracy DOUBLE PRECISION DEFAULT NULL;

COMMENT ON COLUMN pipeline_runs.classification_accuracy IS
    'Fraction (0.0–1.0) of Groq/Gemini classifications that fell within ±15 importance '
    'points of the human-verified label in the held-out eval set. NULL if no eval was '
    'run this period. Populated by scripts/eval_classify_prompt.py and stored here via '
    'the delivery_agent at end-of-run.';

-- Add prompt_version column so we can correlate accuracy with which prompt was active.
ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS prompt_version TEXT DEFAULT 'classify_v1';

COMMENT ON COLUMN pipeline_runs.prompt_version IS
    'Version of classify_*.txt active during this run (e.g. classify_v1, classify_v2). '
    'Set by llm_agent.py from the CLASSIFY_PROMPT_VERSION env/config value.';


-- ==========================================
-- Migration: 20260601000010_add_web_app_policies.sql
-- ==========================================
-- Supabase Migration: 20260601000010_add_web_app_policies.sql
-- Exposes database tables read-only to the public/anon role for the web explorer
-- Enables user feedback submission from the browser dashboard

-- 1. Enable SELECT on articles
DROP POLICY IF EXISTS "Allow public read-only access to articles" ON articles;
CREATE POLICY "Allow public read-only access to articles" ON articles
  FOR SELECT USING (true);

-- 2. Enable SELECT on classifications
DROP POLICY IF EXISTS "Allow public read-only access to classifications" ON classifications;
CREATE POLICY "Allow public read-only access to classifications" ON classifications
  FOR SELECT USING (true);

-- 3. Enable SELECT on insights
DROP POLICY IF EXISTS "Allow public read-only access to insights" ON insights;
CREATE POLICY "Allow public read-only access to insights" ON insights
  FOR SELECT USING (true);

-- 4. Enable SELECT on sources
DROP POLICY IF EXISTS "Allow public read-only access to sources" ON sources;
CREATE POLICY "Allow public read-only access to sources" ON sources
  FOR SELECT USING (true);

-- 5. Enable SELECT on entities
DROP POLICY IF EXISTS "Allow public read-only access to entities" ON entities;
CREATE POLICY "Allow public read-only access to entities" ON entities
  FOR SELECT USING (true);

-- 6. Enable SELECT on article_entities
DROP POLICY IF EXISTS "Allow public read-only access to article_entities" ON article_entities;
CREATE POLICY "Allow public read-only access to article_entities" ON article_entities
  FOR SELECT USING (true);

-- 7. Configure user_feedback policies
-- Drop the restrictive or old policies if present
DROP POLICY IF EXISTS "Allow public select on user_feedback" ON user_feedback;
DROP POLICY IF EXISTS "Allow public insert on user_feedback" ON user_feedback;
DROP POLICY IF EXISTS "Allow public update on user_feedback" ON user_feedback;

-- Create policies for public access (anon role)
CREATE POLICY "Allow public select on user_feedback" ON user_feedback
  FOR SELECT USING (true);

CREATE POLICY "Allow public insert on user_feedback" ON user_feedback
  FOR INSERT WITH CHECK (true);

CREATE POLICY "Allow public update on user_feedback" ON user_feedback
  FOR UPDATE USING (true) WITH CHECK (true);


