import os
import sentry_sdk
from dotenv import load_dotenv

import json
import uuid
import datetime
from supabase import create_client, Client

def init_observability():
    """
    Initializes LangSmith tracing and Sentry error tracking.
    This should be called at the very top of every agent module.
    """
    # Attempt to load local environment variables
    load_dotenv(".env.local")
    
    # --- LangSmith Setup ---
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_PROJECT"] = "glacex-ai"
    
    # The pipeline.yml provides LANGSMITH_API_KEY. LangChain natively looks for LANGCHAIN_API_KEY.
    if "LANGSMITH_API_KEY" in os.environ and "LANGCHAIN_API_KEY" not in os.environ:
        os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]

    # --- Sentry Setup ---
    sentry_dsn = os.environ.get("SENTRY_DSN")
    if sentry_dsn:
        sentry_sdk.init(
            dsn=sentry_dsn,
            traces_sample_rate=0.1,   # 10% of traces for perf monitoring
            environment=os.environ.get("ENVIRONMENT", "production"),
            release="glacex@1.0.0",
        )
    else:
        print("Warning: SENTRY_DSN not set. Error tracking is disabled.")

STATE_FILE = "pipeline_state.json"

def get_supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    if url and key:
        try:
            return create_client(url, key)
        except Exception as e:
            print(f"Failed to create Supabase client in observability: {e}")
    return None

def init_pipeline_run(run_id=None) -> str:
    """Initializes the pipeline run state locally."""
    if not run_id:
        run_id = str(uuid.uuid4())
    
    state = {
        "run_id": run_id,
        "sources_total": 0,
        "sources_successful": 0,
        "ingested": 0,
        "embedded": 0,
        "duplicates": 0,
        "analyzed": 0,
        "total_llm_attempts": 0,
        "failed_llm_validations": 0,
        "new_signals": 0,
        "delivered": 0,
        "prompt_version": "classify_v1",
        "classification_accuracy": None,
        "start_time": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error initializing local pipeline state: {e}")
        
    return run_id

def load_pipeline_state() -> dict:
    """Loads the current pipeline run state."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading local pipeline state: {e}")
        return {}

def update_pipeline_run_metric(**kwargs):
    """Updates one or more metrics in the local pipeline run state."""
    state = load_pipeline_state()
    if not state:
        # If state doesn't exist, initialize it
        init_pipeline_run()
        state = load_pipeline_state()
        
    for k, v in kwargs.items():
        if k in state:
            state[k] = v
            
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        print(f"Error updating local pipeline state: {e}")

def resolve_active_run_id() -> str:
    """Checks for an active incomplete run in Supabase, or gets the cached one, or creates a new one."""
    state = load_pipeline_state()
    if state and state.get("run_id"):
        return state["run_id"]
    
    client = get_supabase_client()
    if client:
        try:
            res = client.table("run_checkpoints")\
                .select("run_id")\
                .is_("phase_completed_at", "null")\
                .order("phase_started_at", desc=True)\
                .limit(1)\
                .execute()
            if res.data:
                run_id = res.data[0]["run_id"]
                init_pipeline_run(run_id)
                return run_id
        except Exception as e:
            print(f"Error checking run_checkpoints for active run: {e}")
            
    return init_pipeline_run()

def start_phase_checkpoint(run_id: str, phase: str):
    """Upserts start metadata for a run phase in the DB."""
    client = get_supabase_client()
    if not client:
        return
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        client.table("run_checkpoints").upsert({
            "run_id": run_id,
            "phase": phase,
            "phase_started_at": now,
            "phase_completed_at": None,
            "docs_processed": 0
        }).execute()
    except Exception as e:
        print(f"Error starting phase checkpoint for {phase}: {e}")

def complete_phase_checkpoint(run_id: str, phase: str, docs_processed: int = 0):
    """Marks a phase checkpoint as completed in the DB."""
    client = get_supabase_client()
    if not client:
        return
    try:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        client.table("run_checkpoints").update({
            "phase_completed_at": now,
            "docs_processed": docs_processed
        }).eq("run_id", run_id).eq("phase", phase).execute()
    except Exception as e:
        print(f"Error completing phase checkpoint for {phase}: {e}")

def is_phase_completed(run_id: str, phase: str) -> bool:
    """Queries if the specified phase has been completed in the DB."""
    if not run_id:
        return False
    client = get_supabase_client()
    if not client:
        return False
    try:
        res = client.table("run_checkpoints")\
            .select("phase_completed_at")\
            .eq("run_id", run_id)\
            .eq("phase", phase)\
            .execute()
        if res.data and res.data[0].get("phase_completed_at"):
            return True
    except Exception as e:
        print(f"Error checking completion of phase {phase}: {e}")
    return False

if __name__ == "__main__":
    init_observability()
