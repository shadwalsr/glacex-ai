import pytest
import psycopg2
import os
import hashlib
from dotenv import load_dotenv

load_dotenv(".env.local")
DB_URL = os.getenv("SUPABASE_DB_URL")
if DB_URL:
    DB_URL = DB_URL.replace(" ", "%20")

@pytest.fixture
def db_conn():
    assert DB_URL is not None, "SUPABASE_DB_URL is not set"
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False # transactional testing
    yield conn
    conn.rollback()
    conn.close()

def test_article_text_hash_upsert_logic(db_conn):
    cur = db_conn.cursor()
    
    # 1. Insert an article
    clean_text = "Unique article content to test text_hash logic."
    text_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()
    
    cur.execute("""
        INSERT INTO articles (url, title, clean_text, text_hash, status)
        VALUES ('http://test-upsert.com/1', 'Test Title', %s, %s, 'raw')
        RETURNING id, fetch_count;
    """, (clean_text, text_hash))
    
    article_id, fetch_count = cur.fetchone()
    assert fetch_count == 1
    
    # 2. Simulate re-ingestion with same text_hash but different URL/title/status
    cur.execute("""
        INSERT INTO articles (url, title, clean_text, text_hash, status)
        VALUES ('http://test-upsert.com/2', 'Test Title Edited', %s, %s, 'raw')
        ON CONFLICT (text_hash) DO UPDATE SET
            last_seen_at = NOW(),
            fetch_count = articles.fetch_count + 1
        RETURNING id, fetch_count, url, title;
    """, (clean_text, text_hash))
    
    upserted_id, new_fetch_count, url, title = cur.fetchone()
    
    assert upserted_id == article_id
    assert new_fetch_count == 2
    # Ensure that it didn't overwrite the original fields (since DO UPDATE only modified last_seen_at & fetch_count)
    assert url == 'http://test-upsert.com/1'
    assert title == 'Test Title'

def test_embedding_sync_trigger(db_conn):
    cur = db_conn.cursor()
    
    # 1. Insert dummy article
    cur.execute("""
        INSERT INTO articles (url, title, clean_text, text_hash)
        VALUES ('http://test-trigger.com/1', 'Trigger test', 'some text', 'hash123')
        RETURNING id;
    """)
    article_id = cur.fetchone()[0]
    
    # Verify embedding is NULL initially
    cur.execute("SELECT embedding FROM articles WHERE id = %s;", (article_id,))
    assert cur.fetchone()[0] is None
    
    # 2. Insert embedding chunk index 0
    dummy_vector = [0.1] * 384
    cur.execute("""
        INSERT INTO embeddings (article_id, chunk_index, chunk_text, embedding)
        VALUES (%s, 0, 'chunk 0 text', %s);
    """, (article_id, dummy_vector))
    
    # 3. Verify trigger updated articles.embedding
    cur.execute("SELECT embedding FROM articles WHERE id = %s;", (article_id,))
    stored_embedding = cur.fetchone()[0]
    assert stored_embedding is not None
    # Stored embedding returned from psycopg2 is a string representation like '[0.1,0.1,...]'
    assert "0.1" in stored_embedding
