import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")
if DB_URL:
    # URL encode spaces to fix psycopg2 parsing errors with unencoded password spaces
    DB_URL = DB_URL.replace(" ", "%20")

def setup_dedup():
    if not DB_URL:
        print("Error: SUPABASE_DB_URL not found in .env file.")
        return

    print("Connecting to Supabase...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Creating dedup_log table and match_embeddings RPC...")
        schema_sql = """
        -- Dedup decisions log
        CREATE TABLE IF NOT EXISTS dedup_log (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          new_article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
          matched_article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
          similarity FLOAT,
          decision TEXT, -- 'duplicate' or 'unique'
          created_at TIMESTAMPTZ DEFAULT now()
        );

        -- Disable RLS explicitly
        ALTER TABLE dedup_log DISABLE ROW LEVEL SECURITY;

        -- RPC function for vector similarity matching
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
        """
        cursor.execute(schema_sql)

        print("Dedup setup completed successfully!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Failed to setup dedup: {e}")

if __name__ == "__main__":
    setup_dedup()
