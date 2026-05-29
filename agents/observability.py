import os
import sentry_sdk
from dotenv import load_dotenv

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

if __name__ == "__main__":
    init_observability()
