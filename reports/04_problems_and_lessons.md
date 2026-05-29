# Report 4: Problems Encountered, Resolutions, and What Went Right

This report captures the technical challenges faced during the bootstrapping of **GlaceX.ai**, how they were resolved, and the strategic decisions that went right.

---

## 1. Technical Problems Faced & Resolutions

### 1.1 Groq Model Decommissioning
- **Problem:** The originally intended model `llama3-8b-8192` was decommissioned by Groq, causing API failures when sending test completions.
- **Resolution:** Updated model configurations to use `llama-3.1-8b-instant`, which is fully active and highly performant.

### 1.2 Gemini SDK & API Key Incompatibility
- **Problem:** Gemini's official `google-generativeai` python library relies on gRPC, which had compatibility issues with the user's `AQ.` format API key. Furthermore, the `gemini-1.5-flash` model alias resulted in errors.
- **Resolution:** Bypassed the rigid official SDK entirely. Implemented standard HTTP REST calls using `httpx` targeting the `gemini-flash-latest` model on the Google v1beta API. This removed the gRPC dependency and allowed the `AQ.` API key to authenticate successfully.

### 1.3 spaCy Model Installation within `uv` Virtual Environments
- **Problem:** The standard way to download spaCy models (`python -m spacy download en_core_web_sm`) fails inside virtual environments managed by `uv` because `uv` does not bundle standard `pip` inside the venv.
- **Resolution:** Installed the model directly as a package wheel using the direct GitHub releases URL:
  `uv pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1-py3-none-any.whl`

### 1.4 Numpy 2.0 Incompatibility with spaCy/Thinc
- **Problem:** The release of Numpy 2.0.0 broke binary compatibility with the compiled C-extensions in spaCy and Thinc, causing immediate runtime crashes on import.
- **Resolution:** Pinned `numpy<2.0.0` in the `pyproject.toml` dependencies to enforce compatibility.

### 1.5 Windows Console Encoding (cp1252) Crashes
- **Problem:** Attempting to print emojis (e.g., success checkmarks or warning symbols) to the Windows command shell caused encoding crashes because Windows defaults to the `cp1252` encoding.
- **Resolution:** Rewrote terminal output logs to use standard ASCII markers like `[SUCCESS]`, `[ERROR]`, and `[PENDING]`.

### 1.6 Space Character in Supabase Password
- **Problem:** The Supabase database password contains spaces (`wzrn gzqy nkof rsqa`), which breaks standard URI DSN parsing in `psycopg2` and generic connection utilities.
- **Resolution:** Encoded the spaces or replaced them programmatically using `.replace(" ", "%20")` in the database connection builder.

### 1.7 arXiv RSS Redirect handling
- **Problem:** Querying the arXiv RSS feed returned a HTTP 301 redirect. The default `httpx.get` call does not follow redirects, leading to an empty parse result.
- **Resolution:** Enabled `follow_redirects=True` explicitly in the HTTPX call.

### 1.8 Hatchling Build Package Structure
- **Problem:** Since the project uses a flat root structure rather than a `src/` layout, the Hatchling build system complained about not finding packages.
- **Resolution:** Declared explicit package targets in `pyproject.toml` to guide Hatchling's wheel discovery.

---

## 2. What Went Right (Successes)

### 2.1 Lightning-Fast Package and Venv Management via `uv`
- **Why it worked:** Using Astro-fast `uv` instead of standard `poetry` or `pip` resulted in near-instant virtual environment generation and dependency installation, dramatically reducing local iteration time.

### 2.2 Seed & Validate Verification Scripts
- **Why it worked:** Creating `scripts/validate_env.py` and `scripts/verify_models.py` before writing agent code ensured that all credentials, database connectivity, and LLM providers were 100% verified working. We identified model decommissioning and SDK auth issues *before* building complex agent pipelines.

### 2.3 Supabase and pgvector Setup
- **Why it worked:** The database schema was successfully injected on the first attempt. Disabling Row Level Security (RLS) allowed the pipeline scripts to read and write records securely without configuring complicated OAuth or JWT client flows.

### 2.4 Modular GitHub Actions Pipeline
- **Why it worked:** Breaking down the ingestion into a 5-phase job structure with built-in caching for both dependencies and HuggingFace models (`~/.cache/huggingface`) protects the budget by keeping the pipeline run under 3 minutes, conserving GitHub Actions monthly free tier minutes.

### 2.5 ntfy.sh Channel Validation
- **Why it worked:** The push notification channel `glacex_ai_pipeline` was verified and linked cleanly via token headers, ensuring delivery reports can be sent directly to devices instantly.
