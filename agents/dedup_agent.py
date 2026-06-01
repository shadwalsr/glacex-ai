import os
import re
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import sentry_sdk
from supabase import create_client, Client
from rank_bm25 import BM25Okapi

from agents.observability import init_observability, update_pipeline_run_metric, resolve_active_run_id, start_phase_checkpoint, complete_phase_checkpoint, is_phase_completed

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Initialize observability
init_observability()

# Load env
load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in env")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

def tokenize(text: str) -> list[str]:
    return re.findall(r'\b\w+\b', text.lower())

def rrf_score(vector_rank: int, bm25_rank: int, k: int = 60) -> float:
    return 1/(k + vector_rank) + 1/(k + bm25_rank)

def is_duplicate(article_id, vector_matches, bm25_score) -> bool:
    if not vector_matches and bm25_score < 12:
        return False
    if vector_matches and vector_matches[0]["similarity"] > 0.92:
        return True  # Very high confidence duplicate
    # Use RRF for borderline cases
    rrf = rrf_score(
      vector_rank=1 if vector_matches else 100,
      bm25_rank=1 if bm25_score > 15 else 100
    )
    return rrf > 0.025  # tunable threshold


def run_dedup():
    logger.info("Phase 3: Hybrid Deduplication Engine starting...")
    from agents.circuit_breaker import is_supabase_open
    if is_supabase_open():
        logger.error("Supabase circuit breaker is OPEN. Aborting run gracefully.")
        return

    run_id = resolve_active_run_id()
    if is_phase_completed(run_id, "dedup"):
        logger.info("Phase 3 (dedup) already completed for this run. Skipping.")
        return

    start_phase_checkpoint(run_id, "dedup")

    try:
        # Fetch articles ready for deduplication (status = 'embedded')
        res = supabase.table("articles")\
            .select("id, title")\
            .eq("status", "embedded")\
            .limit(100)\
            .execute()
            
        new_articles = res.data or []
        if not new_articles:
            logger.info("No embedded articles found for deduplication. Exiting.")
            complete_phase_checkpoint(run_id, "dedup", 0)
            return
            
        logger.info(f"Found {len(new_articles)} articles to dedup.")

        # Build BM25 corpus from recent titles (last 7 days, excluding raw)
        recent_res = supabase.table("articles")\
            .select("id, title")\
            .neq("status", "raw")\
            .gt("scraped_at", (datetime.now(timezone.utc) - timedelta(days=7)).isoformat())\
            .execute()
            
        recent_articles = recent_res.data or []
        
        # We also want to exclude the current batch from the corpus to avoid self-matching
        new_ids = {a["id"] for a in new_articles}
        corpus_articles = [a for a in recent_articles if a["id"] not in new_ids]
        
        corpus = [tokenize(a["title"] or "") for a in corpus_articles]
        
        bm25 = BM25Okapi(corpus) if corpus else None
        
        updates_to_run = []
        logs_to_insert = []
        
        pgvector_threshold = 0.85  # Lowered slightly for RRF borderline check
        
        for article in new_articles:
            article_id = article["id"]
            title = article.get("title") or ""
            matched_id = None
            similarity_score = 0.0
            
            vector_matches = []
            bm25_score = 0.0
            
            # 1. Pgvector Check
            emb_res = supabase.table("embeddings")\
                .select("embedding")\
                .eq("article_id", article_id)\
                .eq("chunk_index", 0)\
                .execute()
                
            if emb_res.data and emb_res.data[0].get("embedding"):
                query_emb = emb_res.data[0]["embedding"]
                match_res = supabase.rpc("match_embeddings", {
                    "query_embedding": query_emb,
                    "match_threshold": pgvector_threshold,
                    "match_count": 5
                }).execute()
                
                # Filter out self-matches
                vector_matches = [m for m in (match_res.data or []) if m["article_id"] != article_id]
            
            # 2. BM25 Check
            if bm25 and title:
                scores = bm25.get_scores(tokenize(title))
                if scores.any():
                    top_score = max(scores)
                    bm25_score = float(top_score)
                    top_index = scores.argmax()
                    matched_id = corpus_articles[top_index]["id"]
            
            # 3. RRF Decision Fusion
            duplicate_flag = is_duplicate(article_id, vector_matches, bm25_score)
            
            if duplicate_flag:
                if vector_matches and vector_matches[0]["similarity"] > 0.92:
                    matched_id = vector_matches[0]["article_id"]
                    similarity_score = vector_matches[0]["similarity"]
                    logger.info(f"Vector duplicate found for {article_id}. Match: {matched_id} (Score: {similarity_score:.3f})")
                else:
                    similarity_score = bm25_score
                    logger.info(f"RRF borderline duplicate found for {article_id}. Match: {matched_id} (BM25: {bm25_score:.1f})")
            
            # Record decision
            decision = "duplicate" if duplicate_flag else "unique"
            new_status = "duplicate" if duplicate_flag else "deduplicated"
            
            updates_to_run.append((article_id, new_status))
            
            logs_to_insert.append({
                "new_article_id": article_id,
                "matched_article_id": matched_id,
                "similarity": similarity_score if matched_id else None,
                "decision": decision
            })
        
        # Apply updates
        for a_id, status in updates_to_run:
            try:
                supabase.table("articles").update({"status": status}).eq("id", a_id).execute()
            except Exception as e:
                logger.error(f"Failed to update status for {a_id}: {e}")
                
        if logs_to_insert:
            try:
                supabase.table("dedup_log").insert(logs_to_insert).execute()
            except Exception as e:
                logger.error(f"Failed to insert dedup logs: {e}")
                
        dup_count = sum(1 for log in logs_to_insert if log.get("decision") == "duplicate")
        logger.info(f"[SUCCESS] Deduplicated {len(new_articles)} articles. Found {dup_count} duplicates.")
        update_pipeline_run_metric(duplicates=dup_count)
        complete_phase_checkpoint(run_id, "dedup", len(new_articles))
        
    except Exception as e:
        logger.error(f"Dedup phase failed: {e}")
        sentry_sdk.capture_exception(e)
        raise e

if __name__ == "__main__":
    run_dedup()
