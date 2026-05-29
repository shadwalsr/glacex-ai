from agents.observability import init_observability
import sentry_sdk

init_observability()

def run_ingestion():
    print("Phase 1: Ingestion starting...")
    try:
        # TODO: Implement scraping routing
        pass
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise e

if __name__ == "__main__":
    run_ingestion()
