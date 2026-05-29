from agents.observability import init_observability
import sentry_sdk

init_observability()

def run_analysis():
    print("Phase 4: LLM Analysis starting...")
    try:
        # TODO: Implement Groq and Gemini dual-LLM logic
        pass
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise e

if __name__ == "__main__":
    run_analysis()
