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
