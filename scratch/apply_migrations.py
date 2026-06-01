import os
import sys
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

def apply_migrations():
    # Load env vars
    PROJECT_ROOT = Path(__file__).resolve().parents[1]
    load_dotenv(PROJECT_ROOT / ".env.local")
    load_dotenv(PROJECT_ROOT / ".env")

    db_url = os.getenv("SUPABASE_DB_URL")
    if not db_url:
        print("Error: SUPABASE_DB_URL is missing in environment variables.", file=sys.stderr)
        sys.exit(1)

    # Format the URL if psycopg2 needs it (remove whitespace, etc.)
    db_url = db_url.strip().replace(" ", "%20")
    if db_url.startswith('"') and db_url.endswith('"'):
        db_url = db_url[1:-1]

    migration_file = PROJECT_ROOT / "supabase" / "migrations" / "20260601000010_add_web_app_policies.sql"
    if not migration_file.exists():
        print(f"Error: Migration file {migration_file} not found.", file=sys.stderr)
        sys.exit(1)

    print(f"Reading migration file: {migration_file.name}")
    with open(migration_file, "r") as f:
        sql = f.read()

    print("Connecting to Supabase Database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        with conn.cursor() as cursor:
            print("Applying RLS policies migration...")
            cursor.execute(sql)
        conn.close()
        print("Policies successfully applied to the database!")
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    apply_migrations()
