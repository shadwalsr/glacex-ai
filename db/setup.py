import os
import psycopg2
from dotenv import load_dotenv

load_dotenv(".env.local")

DB_URL = os.getenv("SUPABASE_DB_URL")
if DB_URL:
    DB_URL = DB_URL.replace(" ", "%20")

def setup_database():
    if not DB_URL:
        print("Error: SUPABASE_DB_URL not found in env.")
        return

    print("Connecting to Supabase...")
    try:
        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        migrations_dir = os.path.join(os.path.dirname(__file__), "..", "supabase", "migrations")
        if not os.path.exists(migrations_dir):
            print(f"Migrations directory not found at {migrations_dir}")
            return
            
        migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
        print(f"Found {len(migration_files)} migrations to apply:")
        for file in migration_files:
            print(f" - {file}")
            
        for file in migration_files:
            migration_path = os.path.join(migrations_dir, file)
            print(f"Applying migration: {file}...")
            with open(migration_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            cursor.execute(schema_sql)
            
        print("All migrations successfully applied!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Failed to setup database: {e}")

if __name__ == "__main__":
    setup_database()
