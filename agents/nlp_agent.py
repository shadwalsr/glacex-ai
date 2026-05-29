from agents.observability import init_observability
import sentry_sdk

init_observability()

def run_nlp():
    print("Phase 2: NLP Embed & NER starting...")
    try:
        # TODO: Implement Sentence-Transformers and spaCy logic
        pass
    except Exception as e:
        sentry_sdk.capture_exception(e)
        raise e

if __name__ == "__main__":
    run_nlp()
