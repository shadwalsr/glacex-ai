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
    )
    ON CONFLICT (text_hash) DO UPDATE SET
      last_seen_at = NOW(),
      fetch_count = articles.fetch_count + 1;
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
  -- A. Upsert core article based on unique text_hash constraint
  INSERT INTO articles (
    url, title, raw_html, clean_text, published_at, status, text_hash, source_id, last_seen_at, fetch_count
  ) VALUES (
    p_article_url, p_article_title, p_article_raw_html, p_article_clean_text, p_article_published_at, p_article_status, p_article_text_hash, p_source_id, NOW(), 1
  )
  ON CONFLICT (text_hash) DO UPDATE SET
    last_seen_at = NOW(),
    fetch_count = articles.fetch_count + 1
  RETURNING id INTO v_article_id;
  
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
