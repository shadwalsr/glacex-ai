import os
import logging
import httpx
import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

logger = logging.getLogger(__name__)

load_dotenv(".env.local")

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "glacex_ai_pipeline")
NTFY_TOKEN = os.getenv("NTFY_TOKEN")

def load_notification_settings():
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "notification_settings.yaml")
    defaults = {
        "high_threshold": 85,
        "digest_threshold": 60,
        "max_per_run": 10,
        "quiet_hours": {
            "enabled": True,
            "start": 22,
            "end": 6
        }
    }
    if not os.path.exists(config_path):
        return defaults
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        
        merged = {}
        merged["high_threshold"] = data.get("high_threshold", defaults["high_threshold"])
        merged["digest_threshold"] = data.get("digest_threshold", defaults["digest_threshold"])
        merged["max_per_run"] = data.get("max_per_run", defaults["max_per_run"])
        
        qh_data = data.get("quiet_hours") or {}
        merged["quiet_hours"] = {
            "enabled": qh_data.get("enabled", defaults["quiet_hours"]["enabled"]),
            "start": qh_data.get("start", defaults["quiet_hours"]["start"]),
            "end": qh_data.get("end", defaults["quiet_hours"]["end"])
        }
        return merged
    except Exception as e:
        logger.warning(f"Error loading notification settings, using defaults: {e}")
        return defaults

def check_quiet_hours(current_hour: int, start: int, end: int) -> bool:
    if start == end:
        return False
    if start > end:
        return current_hour >= start or current_hour < end
    else:
        return start <= current_hour < end

def map_importance_to_priority(importance_val) -> int:
    """Maps importance (0-100 or 1-10) to ntfy priority (1-5)."""
    if importance_val is None:
        return 3 # default
        
    try:
        val = float(importance_val)
        if val <= 10.0:
            val = val * 10.0 # scale up 1-10 to 0-100
            
        if val >= 90.0:
            return 5
        elif val >= 70.0:
            return 4
        elif val >= 50.0:
            return 3
        elif val >= 30.0:
            return 2
        else:
            return 1
    except Exception:
        return 3

def send_insight_push(headline: str, message_body: str, url: str, category: str, priority: int, is_digest: bool = False, article_id: str = None) -> bool:
    """Sends a single push notification to ntfy.sh."""
    if not NTFY_TOPIC:
        logger.error("NTFY_TOPIC is not configured, skipping push.")
        return False
        
    url_endpoint = f"https://ntfy.sh/{NTFY_TOPIC}"
    
    # Trim to limits
    title = headline[:60]
    message = message_body if is_digest else message_body[:80]
    
    headers = {
        "Title": title,
        "Priority": str(priority),
        "Tags": category or "info",
    }
    
    if url:
        headers["Click"] = url
        
    if NTFY_TOKEN:
        headers["Authorization"] = f"Bearer {NTFY_TOKEN}"

    if article_id and not is_digest:
        github_repo = os.getenv("GITHUB_REPOSITORY", "shadwalsr/glacex-ai")
        # Define Action buttons that dispatch feedback event webhooks
        headers["Actions"] = (
            f"http, Good Signal, https://api.github.com/repos/{github_repo}/dispatches, "
            f"body='{{\"event_type\": \"feedback\", \"client_payload\": {{\"article_id\": \"{article_id}\", \"rating\": \"good\"}}}}', "
            f"headers='{{\"Accept\": \"application/vnd.github.v3+json\"}}'; "
            f"http, Noise, https://api.github.com/repos/{github_repo}/dispatches, "
            f"body='{{\"event_type\": \"feedback\", \"client_payload\": {{\"article_id\": \"{article_id}\", \"rating\": \"noise\"}}}}', "
            f"headers='{{\"Accept\": \"application/vnd.github.v3+json\"}}'"
        )

    from agents.circuit_breaker import PersistentCircuitBreaker, CircuitBreakerOpenException
    breaker = PersistentCircuitBreaker("ntfy")

    def perform_post():
        response = httpx.post(url_endpoint, headers=headers, content=message.encode('utf-8'), timeout=15)
        if response.status_code == 200:
            return True
        else:
            raise Exception(f"ntfy.sh push delivery failed: {response.status_code} - {response.text}")

    try:
        return breaker.call(perform_post)
    except CircuitBreakerOpenException:
        logger.warning("ntfy.sh circuit breaker is OPEN. Skipping push notification.")
        return False
    except Exception as e:
        logger.error(f"Error during ntfy push: {e}")
        return False

def deliver_pending_insights():
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Supabase config variables missing, cannot run push delivery.")
        return

    # Load settings
    settings = load_notification_settings()
    
    # Check quiet hours
    if settings.get("quiet_hours", {}).get("enabled", False):
        qh = settings["quiet_hours"]
        current_hour = datetime.datetime.now().hour
        if check_quiet_hours(current_hour, qh["start"], qh["end"]):
            logger.info(f"Currently in quiet hours ({qh['start']} - {qh['end']}). Deferring notification delivery.")
            return

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # 1. Fetch already delivered insights
    try:
        del_res = supabase.table("deliveries").select("insight_id").eq("channel", "ntfy").execute()
        delivered_ids = {d["insight_id"] for d in (del_res.data or []) if d.get("insight_id")}
    except Exception as e:
        logger.error(f"Failed to fetch delivered log: {e}")
        return

    # 2. Fetch insights
    try:
        ins_res = supabase.table("insights")\
            .select("id, headline, tldr, category, article_id")\
            .execute()
        insights = ins_res.data or []
    except Exception as e:
        logger.error(f"Failed to fetch insights: {e}")
        return

    # Filter out already delivered insights
    pending = []
    for ins in insights:
        if ins["id"] not in delivered_ids:
            pending.append(ins)

    if not pending:
        logger.info("No pending insights for mobile push notification.")
        return

    # Fetch articles and classifications for ALL pending insights to join in memory
    article_ids = [ins["article_id"] for ins in pending if ins.get("article_id")]
    
    articles_map = {}
    if article_ids:
        try:
            art_res = supabase.table("articles").select("id, url").in_("id", article_ids).execute()
            articles_map = {a["id"]: a for a in (art_res.data or [])}
        except Exception as e:
            logger.error(f"Failed to fetch articles: {e}")

    classifications_map = {}
    if article_ids:
        try:
            cls_res = supabase.table("classifications").select("article_id, importance").in_("article_id", article_ids).execute()
            classifications_map = {c["article_id"]: c for c in (cls_res.data or [])}
        except Exception as e:
            logger.error(f"Failed to fetch classifications: {e}")

    # Prepare detailed info on pending insights
    prepared_pending = []
    for ins in pending:
        insight_id = ins["id"]
        headline = ins.get("headline") or "New Insight"
        tldr_list = ins.get("tldr") or []
        tldr_bullet = tldr_list[0] if (isinstance(tldr_list, list) and len(tldr_list) > 0) else "Check out this update."
        
        art_id = ins.get("article_id")
        art = articles_map.get(art_id) if art_id else None
        url = art.get("url") if art else ""
        
        cls = classifications_map.get(art_id) if art_id else None
        importance = cls.get("importance") if cls else None
        
        category = ins.get("category") or "news"
        prepared_pending.append({
            "id": insight_id,
            "article_id": art_id,  # preserved for feedback action buttons
            "headline": headline,
            "tldr_bullet": tldr_bullet,
            "url": url,
            "importance": importance,
            "category": category
        })

    # Sort descending by relevance score (importance). Treat None importance as 50.0.
    prepared_pending.sort(key=lambda x: float(x["importance"]) if x.get("importance") is not None else 50.0, reverse=True)

    high_threshold = settings["high_threshold"]
    digest_threshold = settings["digest_threshold"]
    max_per_run = settings["max_per_run"]

    high_tier = []
    digest_tier = []
    low_tier = []

    for ins in prepared_pending:
        importance = ins.get("importance")
        score = float(importance) if importance is not None else 50.0
        if score > high_threshold:
            high_tier.append(ins)
        elif score >= digest_threshold:
            digest_tier.append(ins)
        else:
            low_tier.append(ins)

    total_pushes_sent = 0

    # Process Low Tier (Filtered/Stored only): Mark as delivered/processed immediately
    if low_tier:
        logger.info(f"Marking {len(low_tier)} low-score (<{digest_threshold}) insights as filtered without push.")
        for ins in low_tier:
            try:
                supabase.table("deliveries").insert({
                    "insight_id": ins["id"],
                    "channel": "ntfy",
                    "payload": {
                        "status": "filtered_low_score",
                        "importance": ins["importance"]
                    }
                }).execute()
            except Exception as e:
                logger.error(f"Failed to log filtered status for insight {ins['id']}: {e}")

    # Determine what to deliver in this run
    to_push_individual = []
    digest_items = []
    should_push_digest = False

    if len(digest_tier) > 0 and max_per_run > 0:
        should_push_digest = True
        digest_items = digest_tier
        max_high_slots = max_per_run - 1
    else:
        max_high_slots = max_per_run

    to_push_individual = high_tier[:max_high_slots]

    # Send individual high-tier notifications
    for ins in to_push_individual:
        priority = map_importance_to_priority(ins["importance"])
        # Pass article_id so the feedback action buttons (Good Signal / Noise) are attached
        art_id_for_push = ins.get("article_id") or ins.get("id")
        pushed = send_insight_push(ins["headline"], ins["tldr_bullet"], ins["url"], ins["category"], priority, is_digest=False, article_id=art_id_for_push)
        if pushed:
            try:
                supabase.table("deliveries").insert({
                    "insight_id": ins["id"],
                    "channel": "ntfy",
                    "payload": {
                        "title": ins["headline"][:60],
                        "message": ins["tldr_bullet"][:80],
                        "url": ins["url"],
                        "priority": priority,
                        "category": ins["category"]
                    }
                }).execute()
                total_pushes_sent += 1
            except Exception as e:
                logger.error(f"Failed to log delivery for insight {ins['id']}: {e}")

    # Send digest bundle notification
    if should_push_digest and total_pushes_sent < max_per_run:
        digest_lines = []
        for item in digest_items:
            digest_lines.append(f"• {item['headline']}: {item['tldr_bullet'][:80]}")
        digest_message = "\n".join(digest_lines)[:4000]
        
        digest_title = f"Glacex.ai Digest ({len(digest_items)} items)"
        pushed = send_insight_push(digest_title, digest_message, "", "digest", 3, is_digest=True)
        if pushed:
            for item in digest_items:
                try:
                    supabase.table("deliveries").insert({
                        "insight_id": item["id"],
                        "channel": "ntfy",
                        "payload": {
                            "status": "delivered_in_digest",
                            "digest_title": digest_title
                        }
                    }).execute()
                except Exception as e:
                    logger.error(f"Failed to log digest delivery for insight {item['id']}: {e}")
            total_pushes_sent += 1

    logger.info(f"Successfully processed. Total pushes sent: {total_pushes_sent}.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    deliver_pending_insights()
