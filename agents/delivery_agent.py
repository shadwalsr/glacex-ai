from agents.observability import init_observability
import sentry_sdk

init_observability()

def run_delivery():
    print("Phase 5: Delivery starting...")
    try:
        # TODO: Implement ntfy.sh notification logic
        pass
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise e

if __name__ == "__main__":
    run_delivery()
