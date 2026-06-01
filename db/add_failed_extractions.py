import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")
if DB_URL:
    DB_URL = DB_URL.replace(" ", "%20")

def add_failed_extractions():
    if not DB_URL:
        print("Error: SUPABASE_DB_URL not found in .env file.")
        return

    print("Connecting to Supabase to add failed_extractions table...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        sql = """
        CREATE TABLE IF NOT EXISTS failed_extractions (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          doc_id      UUID REFERENCES articles(id) ON DELETE CASCADE,
          model       TEXT,
          raw_output  TEXT,
          error       TEXT,
          run_id      UUID,
          created_at  TIMESTAMPTZ DEFAULT now()
        );
        
        ALTER TABLE failed_extractions DISABLE ROW LEVEL SECURITY;
        """
        cursor.execute(sql)
        print("Successfully created failed_extractions table!")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to add failed_extractions table: {e}")

if __name__ == "__main__":
    add_failed_extractions()
