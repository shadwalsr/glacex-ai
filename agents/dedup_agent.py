from agents.observability import init_observability
import sentry_sdk

init_observability()

def run_dedup():
    print("Phase 3: Deduplication starting...")
    try:
        # TODO: Implement pgvector and rank_bm25 RRF logic
        pass
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise e

if __name__ == "__main__":
    run_dedup()
