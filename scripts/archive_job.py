import os
import json
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def run_archive_job():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Supabase config variables missing. Cannot run archive job.")
        return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # 1. Prune raw ingestion logs older than 90 days
    logger.info("Pruning raw ingestion logs older than 90 days...")
    ninety_days_ago = (datetime.utcnow() - timedelta(days=90)).isoformat()
    try:
        prune_res = supabase.table("raw_ingestion_log")\
            .delete()\
            .lt("created_at", ninety_days_ago)\
            .execute()
        logger.info(f"Successfully pruned {len(prune_res.data or [])} old ingestion logs.")
    except Exception as e:
        logger.error(f"Failed to prune old raw ingestion logs: {e}")

    # 2. Query articles older than 1 year containing text
    logger.info("Identifying articles older than 1 year for archival...")
    one_year_ago = (datetime.utcnow() - timedelta(days=365)).isoformat()
    
    try:
        # Fetch articles older than 1 year where clean_text or raw_html is still not null
        res = supabase.table("articles")\
            .select("id, title, url, raw_html, clean_text, published_at, scraped_at, status, text_hash, source_id")\
            .lt("scraped_at", one_year_ago)\
            .execute()
            
        articles = res.data or []
        # Filter in Python to process only those that actually have clean_text or raw_html present
        to_archive = [a for a in articles if a.get("clean_text") or a.get("raw_html")]
        
        if not to_archive:
            logger.info("No articles older than 1 year require text archival.")
            return

        logger.info(f"Found {len(to_archive)} articles to export to JSONL.")

        # 3. Pull corresponding classifications and insights for self-contained jsonl
        archived_records = []
        article_ids = [a["id"] for a in to_archive]
        
        # Batch fetch classifications in chunks of 100
        classifications_map = {}
        for i in range(0, len(article_ids), 100):
            batch_ids = article_ids[i:i+100]
            c_res = supabase.table("classifications").select("*").in_("article_id", batch_ids).execute()
            for c in (c_res.data or []):
                classifications_map[c["article_id"]] = c

        # Batch fetch insights in chunks of 100
        insights_map = {}
        for i in range(0, len(article_ids), 100):
            batch_ids = article_ids[i:i+100]
            i_res = supabase.table("insights").select("*").in_("article_id", batch_ids).execute()
            for ins in (i_res.data or []):
                insights_map[ins["article_id"]] = ins

        # Compile record structure
        for a in to_archive:
            record = {
                "article": a,
                "classification": classifications_map.get(a["id"]),
                "insight": insights_map.get(a["id"])
            }
            archived_records.append(record)

        # 4. Write archived records to a month-versioned JSONL file
        archive_dir = os.path.join(os.path.dirname(__file__), "..", "archive")
        os.makedirs(archive_dir, exist_ok=True)
        
        timestamp_str = datetime.utcnow().strftime("%Y-%m")
        filename = f"{timestamp_str}-articles.jsonl"
        filepath = os.path.join(archive_dir, filename)
        
        logger.info(f"Writing to archive file: {filepath}")
        with open(filepath, "a", encoding="utf-8") as f:
            for rec in archived_records:
                f.write(json.dumps(rec) + "\n")
                
        logger.info(f"Successfully wrote {len(archived_records)} records to local archive.")

        # 5. Clear large text fields in database (reclaiming space without losing metadata/embeddings)
        logger.info("Setting raw_html and clean_text to NULL in Supabase to reclaim space...")
        updated_count = 0
        for i in range(0, len(article_ids), 100):
            batch_ids = article_ids[i:i+100]
            try:
                # Set raw_html and clean_text to null for this batch
                supabase.table("articles")\
                    .update({"raw_html": None, "clean_text": None})\
                    .in_("id", batch_ids)\
                    .execute()
                updated_count += len(batch_ids)
            except Exception as update_err:
                logger.error(f"Failed to clear text for article batch: {update_err}")

        logger.info(f"Successfully reclaimed storage space for {updated_count} articles.")

    except Exception as e:
        logger.error(f"Error during archival job execution: {e}")

if __name__ == "__main__":
    run_archive_job()
