import pytest
import os
import json
import psycopg2
import shutil
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client
from scripts.archive_job import run_archive_job

load_dotenv(".env.local")
DB_URL = os.getenv("SUPABASE_DB_URL")
if DB_URL:
    DB_URL = DB_URL.replace(" ", "%20")
    
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

@pytest.fixture
def db_conn():
    assert DB_URL is not None
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = True
    yield conn
    conn.close()

@pytest.fixture
def supabase_client():
    assert SUPABASE_URL is not None
    assert SUPABASE_SERVICE_KEY is not None
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def test_raw_ingestion_log_pruning(db_conn):
    cur = db_conn.cursor()
    
    # 1. Insert a dummy source
    unique_url = f"http://log-{uuid.uuid4()}.com"
    cur.execute("INSERT INTO sources (name, url, type) VALUES ('Log Source', %s, 'rss') RETURNING id;", (unique_url,))
    source_id = cur.fetchone()[0]
    
    # 2. Insert logs: one 95 days old (should prune), one 10 days old (should keep)
    old_time = (datetime.utcnow() - timedelta(days=95)).isoformat()
    new_time = (datetime.utcnow() - timedelta(days=10)).isoformat()
    
    cur.execute("""
        INSERT INTO raw_ingestion_log (source_id, status, created_at)
        VALUES (%s, 'success', %s) RETURNING id;
    """, (source_id, old_time))
    old_log_id = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO raw_ingestion_log (source_id, status, created_at)
        VALUES (%s, 'success', %s) RETURNING id;
    """, (source_id, new_time))
    new_log_id = cur.fetchone()[0]
    
    # Run the archival job function
    run_archive_job()
    
    # 3. Verify logs table
    cur.execute("SELECT id FROM raw_ingestion_log WHERE id = %s;", (old_log_id,))
    assert cur.fetchone() is None, "Old log was not pruned!"
    
    cur.execute("SELECT id FROM raw_ingestion_log WHERE id = %s;", (new_log_id,))
    assert cur.fetchone() is not None, "New log was mistakenly pruned!"
    
    # Clean up source
    cur.execute("DELETE FROM sources WHERE id = %s;", (source_id,))

def test_article_archival_and_text_clearing(db_conn):
    cur = db_conn.cursor()
    
    # Clear local archive folder if present to avoid interference
    archive_dir = os.path.join(os.path.dirname(__file__), "..", "archive")
    if os.path.exists(archive_dir):
        shutil.rmtree(archive_dir)
        
    # 1. Insert a dummy source
    unique_src_url = f"http://archive-{uuid.uuid4()}.com"
    cur.execute("INSERT INTO sources (name, url, type) VALUES ('Archive Source', %s, 'rss') RETURNING id;", (unique_src_url,))
    source_id = cur.fetchone()[0]
    
    # 2. Insert articles:
    # - one 14 months old (should archive)
    # - one 1 month old (should NOT archive)
    old_scraped = (datetime.utcnow() - timedelta(days=420)).isoformat()
    new_scraped = (datetime.utcnow() - timedelta(days=30)).isoformat()
    
    url_old = f"http://test-arch.com/old-{uuid.uuid4()}"
    url_new = f"http://test-arch.com/new-{uuid.uuid4()}"
    hash_old = f"hash-old-{uuid.uuid4()}"
    hash_new = f"hash-new-{uuid.uuid4()}"
    
    cur.execute("""
        INSERT INTO articles (source_id, url, title, clean_text, raw_html, scraped_at, text_hash)
        VALUES (%s, %s, 'Old Article', 'Old clean text', 'Old HTML', %s, %s) RETURNING id;
    """, (source_id, url_old, old_scraped, hash_old))
    old_art_id = cur.fetchone()[0]
    
    cur.execute("""
        INSERT INTO articles (source_id, url, title, clean_text, raw_html, scraped_at, text_hash)
        VALUES (%s, %s, 'New Article', 'New clean text', 'New HTML', %s, %s) RETURNING id;
    """, (source_id, url_new, new_scraped, hash_new))
    new_art_id = cur.fetchone()[0]
    
    # 3. Add dummy classification and insight to the old article to check if they are exported & preserved
    cur.execute("""
        INSERT INTO classifications (article_id, category, subcategory, importance, is_ai_relevant, technical_depth, reason)
        VALUES (%s, 'paper', 'optimization', 80, true, 'high', 'Classification reason');
    """, (old_art_id,))
    
    cur.execute("""
        INSERT INTO insights (article_id, headline, tldr, technical_depth, practical_utility, ecosystem_impact, tags, category)
        VALUES (%s, 'Old Article Headline', ARRAY['bullet 1', 'bullet 2', 'bullet 3'], 'depth info', 'utility info', 'impact info', ARRAY['tag1', 'tag2'], 'paper');
    """, (old_art_id,))
    
    # Run the archival job function
    run_archive_job()
    
    # 4. Check that old article text columns are set to NULL in db
    cur.execute("SELECT clean_text, raw_html, title, url FROM articles WHERE id = %s;", (old_art_id,))
    clean_text, raw_html, title, url = cur.fetchone()
    assert clean_text is None
    assert raw_html is None
    assert title == 'Old Article'
    assert url == url_old
    
    # Check that classifications and insights remain in the database (permanent)
    cur.execute("SELECT category FROM classifications WHERE article_id = %s;", (old_art_id,))
    assert cur.fetchone()[0] == 'paper'
    
    cur.execute("SELECT headline FROM insights WHERE article_id = %s;", (old_art_id,))
    assert cur.fetchone()[0] == 'Old Article Headline'
    
    # 5. Check that new article is untouched
    cur.execute("SELECT clean_text, raw_html FROM articles WHERE id = %s;", (new_art_id,))
    new_clean, new_raw = cur.fetchone()
    assert new_clean == 'New clean text'
    assert new_raw == 'New HTML'
    
    # 6. Check that the jsonl archive file was generated with older article data
    assert os.path.exists(archive_dir)
    jsonl_files = [f for f in os.listdir(archive_dir) if f.endswith(".jsonl")]
    assert len(jsonl_files) == 1
    
    filepath = os.path.join(archive_dir, jsonl_files[0])
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["article"]["id"] == old_art_id
    assert record["article"]["clean_text"] == 'Old clean text'
    assert record["classification"]["category"] == 'paper'
    assert record["insight"]["headline"] == 'Old Article Headline'
    
    # Clean up database records
    cur.execute("DELETE FROM sources WHERE id = %s;", (source_id,))
    
    # Clean up local archive files
    shutil.rmtree(archive_dir)
