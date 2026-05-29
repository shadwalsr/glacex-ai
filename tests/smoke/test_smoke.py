import os
import psycopg2
import httpx
from playwright.sync_api import sync_playwright
import google.generativeai as genai
from groq import Groq
from sentence_transformers import SentenceTransformer
import spacy
from dotenv import load_dotenv

load_dotenv(".env.local")

DB_URL = os.getenv("SUPABASE_DB_URL")
if DB_URL:
    DB_URL = DB_URL.replace(" ", "%20")

def test_db_connection():
    assert DB_URL is not None, "SUPABASE_DB_URL is not set"
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT 1;")
    res = cur.fetchone()
    assert res[0] == 1
    cur.close()
    conn.close()

def test_pgvector_insert():
    assert DB_URL is not None
    conn = psycopg2.connect(DB_URL)
    conn.autocommit = False
    cur = conn.cursor()
    try:
        # Insert a dummy article
        cur.execute("INSERT INTO articles (url, title) VALUES ('http://test.com/smoke', 'Smoke Test') RETURNING id;")
        article_id = cur.fetchone()[0]
        
        # Insert a zero vector of dim 384
        dummy_vector = [0.0] * 384
        cur.execute("INSERT INTO embeddings (article_id, chunk_index, embedding) VALUES (%s, %s, %s);", (article_id, 0, dummy_vector))
        
        # Test query
        cur.execute("SELECT count(*) FROM embeddings WHERE article_id = %s;", (article_id,))
        count = cur.fetchone()[0]
        assert count == 1
    finally:
        conn.rollback() # Rollback to keep DB clean
        cur.close()
        conn.close()

def test_groq_ping():
    api_key = os.getenv("GROQ_API_KEY")
    assert api_key is not None, "GROQ_API_KEY is not set"
    client = Groq(api_key=api_key)
    completion = client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[{"role": "user", "content": "Hi"}],
        max_tokens=5
    )
    assert completion.choices[0].message.content is not None

def test_gemini_ping():
    api_key = os.getenv("GEMINI_API_KEY")
    assert api_key is not None, "GEMINI_API_KEY is not set"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.0-flash')
    response = model.generate_content("Hi")
    assert response.text is not None

def test_rss_parse():
    # Fetch arXiv cs.AI feed
    response = httpx.get("http://export.arxiv.org/rss/cs.AI", follow_redirects=True)
    assert response.status_code == 200
    assert "<rdf:RDF" in response.text or "<rss" in response.text

def test_playwright_fetch():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com")
        text = page.inner_text("h1")
        assert "Example Domain" in text
        browser.close()

def test_embedding_dim():
    model = SentenceTransformer('BAAI/bge-small-en-v1.5')
    vector = model.encode("test")
    assert len(vector) == 384

def test_ner_extract():
    nlp = spacy.load("en_core_web_sm")
    doc = nlp("Apple is a company based in California.")
    orgs = [ent.text for ent in doc.ents if ent.label_ == "ORG"]
    assert "Apple" in orgs
