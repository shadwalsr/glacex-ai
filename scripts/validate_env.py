import os
import sys
from dotenv import load_dotenv

def validate_environment():
    # Load .env.local if it exists (for local dev pattern)
    load_dotenv(".env.local")

    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_KEY",
        "GROQ_API_KEY",
        "GEMINI_API_KEY",
        "LANGSMITH_API_KEY",
        "SENTRY_DSN",
        "NTFY_TOPIC",
    ]

    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print("❌ FATAL: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease ensure these are set in your .env.local file or injected via GitHub Actions secrets.")
        sys.exit(1)

    print("✅ All required environment variables are present.")

if __name__ == "__main__":
    validate_environment()
