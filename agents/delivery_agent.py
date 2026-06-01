import os
import datetime
import json
import logging
import sentry_sdk
from supabase import create_client, Client
from agents.observability import init_observability, load_pipeline_state, resolve_active_run_id, start_phase_checkpoint, complete_phase_checkpoint, is_phase_completed
from delivery.ntfy_delivery import deliver_pending_insights, send_insight_push

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

init_observability()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def run_delivery():
    logger.info("Phase 5: Delivery and Health Monitoring starting...")
    from agents.circuit_breaker import is_supabase_open
    if is_supabase_open():
        logger.error("Supabase circuit breaker is OPEN. Aborting run gracefully.")
        return
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        logger.error("Supabase config variables missing, cannot run delivery/monitoring.")
        return

    run_id = resolve_active_run_id()
    if is_phase_completed(run_id, "delivery"):
        logger.info("Phase 5 (delivery) already completed for this run. Skipping.")
        return

    start_phase_checkpoint(run_id, "delivery")

    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    # 1. Read the final state from pipeline_state.json
    state = load_pipeline_state()
    if not state:
        logger.warning("No active pipeline state file found. Running delivery pushes only.")
        try:
            deliver_pending_insights()
            complete_phase_checkpoint(run_id, "delivery", 0)
        except Exception as e:
            logger.error(f"Error running delivery pushes: {e}")
            sentry_sdk.capture_exception(e)
        return

    run_id = state.get("run_id")
    sources_total = state.get("sources_total", 0)
    sources_successful = state.get("sources_successful", 0)
    ingested = state.get("ingested", 0)
    embedded = state.get("embedded", 0)
    duplicates = state.get("duplicates", 0)
    analyzed = state.get("analyzed", 0)
    total_llm_attempts = state.get("total_llm_attempts", 0)
    failed_llm_validations = state.get("failed_llm_validations", 0)
    new_signals = state.get("new_signals", 0)
    prompt_version = state.get("prompt_version", "classify_v1")
    classification_accuracy = state.get("classification_accuracy", None)  # None if no eval ran this cycle

    # 2. Run mobile push delivery first so we know how many items are delivered
    delivered_count = 0
    try:
        deliver_pending_insights()
        # Query deliveries table to see how many were sent in this run/log
        # We can just count deliveries logged for ntfy recently
        del_count_res = supabase.table("deliveries")\
            .select("id")\
            .gt("created_at", (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=5)).isoformat())\
            .execute()
        delivered_count = len(del_count_res.data or [])
    except Exception as e:
        logger.error(f"Error running mobile push delivery: {e}")
        sentry_sdk.capture_exception(e)

    # 3. Calculate health metrics
    source_rate = (sources_successful / sources_total) if sources_total > 0 else 1.0
    
    expected_new_signals = 5  # default
    signal_ratio = (new_signals / expected_new_signals)
    # Cap signal ratio to 1.0 to keep health score bounded to 0-1
    signal_yield = min(signal_ratio, 1.0)
    
    llm_success_rate = 1.0
    if total_llm_attempts > 0:
        llm_success_rate = (total_llm_attempts - failed_llm_validations) / total_llm_attempts

    health_score = (source_rate * 0.4) + (signal_yield * 0.4) + (llm_success_rate * 0.2)
    logger.info(f"Computed health_score: {health_score:.3f} (source_rate={source_rate:.2f}, signal_yield={signal_yield:.2f}, llm_success_rate={llm_success_rate:.2f})")

    # 4. Check consecutive failures by fetching previous run's health score
    consecutive_failures = False
    try:
        prev_health = supabase.table("pipeline_health")\
            .select("health_score")\
            .order("created_at", desc=True)\
            .limit(1)\
            .execute()
        
        if prev_health.data:
            prev_score = prev_health.data[0]["health_score"]
            logger.info(f"Previous run health score: {prev_score:.3f}")
            if health_score < 0.5 and prev_score < 0.5:
                consecutive_failures = True
    except Exception as e:
        logger.error(f"Failed to check previous health score: {e}")

    # Fire alert if health_score < 0.5 for 2 consecutive runs
    if consecutive_failures:
        alert_msg = f"CRITICAL: Pipeline Health Score has fallen below 0.5 for 2 consecutive runs! Current score: {health_score:.3f}."
        logger.error(alert_msg)
        sentry_sdk.capture_message(alert_msg, level="error")
        # Send ntfy push to self (priority 5 = max/critical)
        send_insight_push(
            headline="Pipeline Health Degraded",
            message_body=alert_msg,
            url="",
            category="health",
            priority=5,
            is_digest=False
        )

    # 5. Log to pipeline_runs table
    duration_s = 0
    if state.get("start_time"):
        try:
            start_dt = datetime.datetime.fromisoformat(state["start_time"])
            duration_s = int((datetime.datetime.now(datetime.timezone.utc) - start_dt).total_seconds())
        except Exception:
            pass

    try:
        supabase.table("pipeline_runs").insert({
            "id": run_id,
            "ingested": ingested,
            "embedded": embedded,
            "duplicates": duplicates,
            "new_signals": new_signals,
            "analyzed": analyzed,
            "delivered": delivered_count,
            "duration_s": duration_s,
            "prompt_version": prompt_version,
            "classification_accuracy": classification_accuracy,
        }).execute()
        logger.info(f"Successfully logged stats to pipeline_runs table for run {run_id}.")
    except Exception as e:
        logger.error(f"Failed to log run stats to pipeline_runs: {e}")
        sentry_sdk.capture_exception(e)

    # 6. Log to pipeline_health table
    try:
        supabase.table("pipeline_health").insert({
            "run_id": run_id,
            "sources_successful": sources_successful,
            "sources_total": sources_total,
            "new_signals": new_signals,
            "expected_new_signals": expected_new_signals,
            "llm_success_rate": llm_success_rate,
            "health_score": health_score
        }).execute()
        logger.info(f"Successfully logged health score to pipeline_health table for run {run_id}.")
    except Exception as e:
        logger.error(f"Failed to log health score to pipeline_health: {e}")
        sentry_sdk.capture_exception(e)

    complete_phase_checkpoint(run_id, "delivery", delivered_count)

    # 7. Clean up pipeline_state.json
    STATE_FILE = "pipeline_state.json"
    if os.path.exists(STATE_FILE):
        try:
            os.remove(STATE_FILE)
            logger.info("Cleaned up local pipeline state file.")
        except Exception as e:
            logger.error(f"Failed to delete local state file: {e}")

if __name__ == "__main__":
    try:
        run_delivery()
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise e
