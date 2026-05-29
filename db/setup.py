import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")
if DB_URL:
    # URL encode spaces to fix psycopg2 parsing errors with unencoded password spaces
    DB_URL = DB_URL.replace(" ", "%20")

def setup_database():
    if not DB_URL:
        print("Error: SUPABASE_DB_URL not found in .env file.")
        return

    print("Connecting to Supabase...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        print("Dropping old tables...")
        cursor.execute("DROP TABLE IF EXISTS deliveries, intelligence, embeddings, document_embeddings, articles, sources CASCADE;")

        print("Applying exact schema with indexes and disabled RLS...")
        schema_sql = """
        -- Enable pgvector
        CREATE EXTENSION IF NOT EXISTS vector;

        -- Sources registry
        CREATE TABLE sources (
          id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name          TEXT NOT NULL,
          url           TEXT NOT NULL UNIQUE,
          type          TEXT CHECK(type IN ('rss','playwright','httpx')),
          category      TEXT,           -- 'newsletter','arxiv','twitter','hn','product'
          active        BOOLEAN DEFAULT true,
          last_scraped  TIMESTAMPTZ,
          scrape_config JSONB           -- rate limits, selectors, auth
        );

        -- Raw articles (archive everything)
        CREATE TABLE articles (
          id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          source_id     UUID REFERENCES sources(id) ON DELETE CASCADE,
          url           TEXT NOT NULL UNIQUE,
          title         TEXT,
          raw_html      TEXT,
          clean_text    TEXT,
          published_at  TIMESTAMPTZ,
          scraped_at    TIMESTAMPTZ DEFAULT now(),
          status        TEXT DEFAULT 'raw'  -- raw|embedded|analyzed|delivered
        );

        -- Embeddings store
        CREATE TABLE embeddings (
          id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          article_id    UUID REFERENCES articles(id) ON DELETE CASCADE,
          chunk_index   INT DEFAULT 0,
          chunk_text    TEXT,
          embedding     vector(384),        -- bge-small-en-v1.5 dim
          created_at    TIMESTAMPTZ DEFAULT now()
        );
        CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops)
          WITH (lists = 100);

        -- Curated intelligence items
        CREATE TABLE intelligence (
          id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          article_id    UUID REFERENCES articles(id) ON DELETE CASCADE,
          category      TEXT,    -- 'paper'|'tool'|'product'|'company'|'newsletter'
          title         TEXT,
          summary       TEXT,
          key_signals   JSONB,   -- entities, metrics, technical claims
          importance    INT,     -- 1-10 score from LLM
          tags          TEXT[],
          created_at    TIMESTAMPTZ DEFAULT now()
        );

        -- Delivery log (idempotency)
        CREATE TABLE deliveries (
          id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          intelligence_id UUID REFERENCES intelligence(id) ON DELETE CASCADE,
          channel       TEXT,    -- 'ntfy'
          delivered_at  TIMESTAMPTZ DEFAULT now(),
          payload       JSONB
        );

        -- Indexes & performance
        CREATE INDEX ON articles(status);
        CREATE INDEX ON articles(scraped_at DESC);
        CREATE INDEX ON intelligence(importance DESC);

        -- Disable RLS explicitly
        ALTER TABLE sources DISABLE ROW LEVEL SECURITY;
        ALTER TABLE articles DISABLE ROW LEVEL SECURITY;
        ALTER TABLE embeddings DISABLE ROW LEVEL SECURITY;
        ALTER TABLE intelligence DISABLE ROW LEVEL SECURITY;
        ALTER TABLE deliveries DISABLE ROW LEVEL SECURITY;
        """
        cursor.execute(schema_sql)

        print("Database exact schema updated perfectly!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Failed to setup database: {e}")

if __name__ == "__main__":
    setup_database()
