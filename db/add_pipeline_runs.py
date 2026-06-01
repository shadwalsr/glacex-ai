import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")
if DB_URL:
    DB_URL = DB_URL.replace(" ", "%20")

def add_pipeline_runs():
    if not DB_URL:
        print("Error: SUPABASE_DB_URL not found in .env file.")
        return

    print("Connecting to Supabase to add pipeline_runs table...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        sql = """
        CREATE TABLE IF NOT EXISTS pipeline_runs (
          id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          run_at      TIMESTAMPTZ DEFAULT now(),
          ingested    INT,
          embedded    INT,
          duplicates  INT,
          new_signals INT,
          analyzed    INT,
          delivered   INT,
          errors      JSONB,
          duration_s  INT
        );
        
        ALTER TABLE pipeline_runs DISABLE ROW LEVEL SECURITY;
        """
        cursor.execute(sql)
        print("Successfully created pipeline_runs table!")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to add pipeline_runs table: {e}")

if __name__ == "__main__":
    add_pipeline_runs()
