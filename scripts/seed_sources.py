import os
import yaml
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

def seed_sources():
    load_dotenv()
    load_dotenv(".env.local")

    DB_URL = os.getenv("SUPABASE_DB_URL")
    if DB_URL:
        DB_URL = DB_URL.replace(" ", "%20")
    else:
        print("Error: SUPABASE_DB_URL is missing.")
        return

    print("Connecting to Supabase...")
    try:
        with open("sources.yaml", "r") as f:
            data = yaml.safe_load(f)
            sources = data.get("sources", [])

        if not sources:
            print("No sources found in sources.yaml.")
            return

        conn = psycopg2.connect(DB_URL)
        conn.autocommit = True
        cursor = conn.cursor()

        print(f"Found {len(sources)} sources to insert.")
        inserted = 0

        for s in sources:
            name = s.get("name")
            url = s.get("url")
            type_ = s.get("type")
            category = s.get("category")
            scrape_config = s.get("scrape_config", {})

            try:
                cursor.execute("""
                    INSERT INTO sources (name, url, type, category, scrape_config)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (url) DO UPDATE 
                    SET name = EXCLUDED.name, 
                        type = EXCLUDED.type, 
                        category = EXCLUDED.category,
                        scrape_config = EXCLUDED.scrape_config;
                """, (name, url, type_, category, Json(scrape_config)))
                inserted += 1
                print(f" -> Inserted/Updated: {name}")
            except Exception as e:
                print(f" -> Failed to insert {name}: {e}")

        print(f"\n✅ Successfully seeded {inserted} sources!")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Script failed: {e}")

if __name__ == "__main__":
    seed_sources()
