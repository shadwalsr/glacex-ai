from agents.observability import init_observability, resolve_active_run_id, start_phase_checkpoint, complete_phase_checkpoint, is_phase_completed
import sentry_sdk
from agents.llm_agent import run_llm_analysis

init_observability()

def run_analysis():
    print("Phase 4: LLM Analysis starting...")
    from agents.circuit_breaker import is_supabase_open
    if is_supabase_open():
        print("Supabase circuit breaker is OPEN. Aborting run gracefully.")
        return

    run_id = resolve_active_run_id()
    if is_phase_completed(run_id, "analysis"):
        print("Phase 4 (analysis) already completed for this run. Skipping.")
        return

    start_phase_checkpoint(run_id, "analysis")
    try:
        run_llm_analysis()
        complete_phase_checkpoint(run_id, "analysis", 1)
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise e

if __name__ == "__main__":
    run_analysis()
