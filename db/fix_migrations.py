import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("SUPABASE_DB_URL")
if DB_URL:
    DB_URL = DB_URL.replace(" ", "%20")

def fix_migrations_error():
    if not DB_URL:
        print("Error: SUPABASE_DB_URL not found in .env file.")
        return

    print("Connecting to Supabase to fix migration error...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        sql = """
        CREATE SCHEMA IF NOT EXISTS supabase_migrations;
        CREATE TABLE IF NOT EXISTS supabase_migrations.schema_migrations (
            version character varying(255) NOT NULL PRIMARY KEY,
            statements text[],
            name character varying(255)
        );
        """
        cursor.execute(sql)
        print("Successfully created supabase_migrations.schema_migrations table!")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Failed to fix migrations error: {e}")

if __name__ == "__main__":
    fix_migrations_error()
