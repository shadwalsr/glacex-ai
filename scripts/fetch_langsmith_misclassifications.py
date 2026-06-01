"""
fetch_langsmith_misclassifications.py

Connects to LangSmith, fetches the last N days of classification traces from
the 'glacex-ai' project, identifies the 20 most common misclassification
patterns, and prints a prioritised report.

Patterns detected:
  1. False Positives  : user_feedback='noise' but importance > 60
  2. False Negatives  : user_feedback='good'  but importance < 50
  3. Failed / Error   : LLM output contains an 'error' key or failed JSON parse
  4. Low Confidence   : output confidence flag set to low (where present)

Usage:
    python scripts/fetch_langsmith_misclassifications.py [--days 28] [--project glacex-ai] [--limit 500]
"""

import argparse
import json
import os
import sys
import textwrap
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Load environment variables from .env.local
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(".env.local")
except ImportError:
    print("[WARN] python-dotenv not installed; skipping .env.local load.")

# ---------------------------------------------------------------------------
# Imports that may be missing
# ---------------------------------------------------------------------------
try:
    from langsmith import Client
except ImportError:
    print(
        "\n[ERROR] 'langsmith' package not installed.\n"
        "  Install it with:  pip install langsmith\n"
        "  or:               uv add langsmith\n"
    )
    sys.exit(1)

try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_json(text: str) -> Optional[dict]:
    """Try to parse JSON; return None on failure."""
    if not isinstance(text, str):
        try:
            return dict(text)
        except Exception:
            return None
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None


def _extract_run_fields(run) -> dict:
    """Pull the fields we care about from a LangSmith Run object."""
    output_raw = getattr(run, "outputs", None) or {}
    input_raw  = getattr(run, "inputs",  None) or {}

    # Flatten one level if nested under 'output' / 'input' key
    if isinstance(output_raw, dict) and "output" in output_raw:
        output_raw = output_raw["output"]
    if isinstance(input_raw, dict) and "input" in input_raw:
        input_raw = input_raw["input"]

    # If still a string, try JSON parse
    if isinstance(output_raw, str):
        output_raw = _safe_json(output_raw) or {"raw": output_raw}
    if isinstance(input_raw, str):
        input_raw = _safe_json(input_raw) or {"raw": input_raw}

    importance  = output_raw.get("importance") if isinstance(output_raw, dict) else None
    category    = output_raw.get("category",  "unknown") if isinstance(output_raw, dict) else "unknown"
    has_error   = isinstance(output_raw, dict) and (
        "error" in output_raw or run.error is not None
    )

    title   = (input_raw.get("title") or input_raw.get("article_title") or "")[:120] \
              if isinstance(input_raw, dict) else ""
    snippet = (input_raw.get("text") or input_raw.get("content") or "")[:200] \
              if isinstance(input_raw, dict) else ""

    return {
        "run_id":     str(run.id),
        "article_id": input_raw.get("article_id") or input_raw.get("id") if isinstance(input_raw, dict) else None,
        "title":      title,
        "snippet":    snippet,
        "importance": importance,
        "category":   category,
        "has_error":  has_error,
        "error_msg":  run.error or (output_raw.get("error") if isinstance(output_raw, dict) else None),
        "start_time": run.start_time,
    }


# ---------------------------------------------------------------------------
# Supabase / Postgres feedback join
# ---------------------------------------------------------------------------

def fetch_feedback_map(supabase_db_url: Optional[str]) -> dict:
    """
    Returns a dict  {article_id: feedback_label}
    where feedback_label is 'good' or 'noise'.
    Falls back to empty dict if DB unavailable.
    """
    if not supabase_db_url:
        print("[INFO] SUPABASE_DB_URL not set — skipping feedback join.")
        return {}
    if psycopg2 is None:
        print("[WARN] psycopg2 not installed — skipping feedback join.")
        return {}

    feedback_map: dict = {}
    try:
        conn = psycopg2.connect(supabase_db_url)
        cur  = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cur.execute(
            "SELECT article_id, feedback FROM user_feedback WHERE feedback IN ('good', 'noise')"
        )
        rows = cur.fetchall()
        for row in rows:
            feedback_map[str(row["article_id"])] = row["feedback"]
        cur.close()
        conn.close()
        print(f"[INFO] Loaded {len(feedback_map)} feedback entries from Supabase.")
    except Exception as exc:
        print(f"[WARN] Could not connect to Supabase: {exc}")
    return feedback_map


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def fetch_runs(client: Client, project: str, days: int, limit: int) -> list[dict]:
    """Fetch and normalise classification LLM runs from LangSmith."""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    print(f"[INFO] Fetching up to {limit} runs from project='{project}' since {since.date()} …")

    runs = []
    try:
        raw_runs = client.list_runs(
            project_name=project,
            run_type="llm",
            start_time=since,
            limit=limit,
            filter='has(name, "classify")',  # LangSmith filter syntax
        )
        for run in raw_runs:
            if "classify" in (run.name or "").lower():
                runs.append(_extract_run_fields(run))
    except Exception as exc:
        print(f"[ERROR] LangSmith query failed: {exc}")
        raise

    print(f"[INFO] Retrieved {len(runs)} matching runs.")
    return runs


def classify_pattern(run: dict, feedback_map: dict) -> Optional[str]:
    """Return a pattern label for this run, or None if no misclassification."""
    article_id = str(run.get("article_id") or "")
    importance = run.get("importance")
    feedback   = feedback_map.get(article_id)

    if run["has_error"]:
        return "ERROR / JSON-parse failure"

    if importance is None:
        return "Missing importance score in output"

    try:
        score = float(importance)
    except (TypeError, ValueError):
        return "Invalid importance score (non-numeric)"

    if feedback == "noise" and score > 60:
        delta = round(score - 60, 1)
        return f"False Positive (noise feedback, score={score:.0f}, +{delta} above threshold)"

    if feedback == "good" and score < 50:
        delta = round(50 - score, 1)
        return f"False Negative (good feedback, score={score:.0f}, -{delta} below threshold)"

    # Human label absent — flag large-confidence deviations heuristically
    if importance is not None:
        try:
            s = float(importance)
            if s <= 5 or s >= 95:
                return f"Extreme score (score={s:.0f}) — potential overconfidence"
        except (TypeError, ValueError):
            pass

    return None  # no pattern detected


def build_pattern_report(runs: list[dict], feedback_map: dict) -> list[tuple[str, list[dict]]]:
    """Group runs by pattern and return sorted by frequency (desc)."""
    pattern_groups: dict[str, list[dict]] = defaultdict(list)

    for run in runs:
        pattern = classify_pattern(run, feedback_map)
        if pattern:
            pattern_groups[pattern].append(run)

    # Sort by frequency descending, take top 20
    sorted_patterns = sorted(pattern_groups.items(), key=lambda x: len(x[1]), reverse=True)
    return sorted_patterns[:20]


def print_report(patterns: list[tuple[str, list[dict]]], total_runs: int, days: int) -> None:
    """Print a human-readable prioritised report."""
    sep = "=" * 80
    print(f"\n{sep}")
    print(f"  GlaceX LangSmith Misclassification Report")
    print(f"  Period  : last {days} days")
    print(f"  Runs analysed : {total_runs}")
    print(f"  Distinct patterns found : {len(patterns)}")
    print(f"{sep}\n")

    if not patterns:
        print("  ✅  No misclassification patterns detected — great job!\n")
        return

    for rank, (pattern, examples) in enumerate(patterns, start=1):
        count = len(examples)
        pct   = 100 * count / total_runs if total_runs else 0
        print(f"  #{rank:02d}  [{count:>4} occurrences | {pct:5.1f}%]  {pattern}")
        print(f"       Sample runs (up to 3):")
        for ex in examples[:3]:
            title   = ex.get("title") or "(no title)"
            snippet = ex.get("snippet") or ""
            run_id  = ex.get("run_id", "")
            ts      = ex.get("start_time")
            ts_str  = ts.strftime("%Y-%m-%d %H:%M UTC") if ts else "?"
            print(f"         • [{ts_str}] run={run_id[:8]}…")
            print(f"           Title  : {textwrap.shorten(title, 80)}")
            if snippet:
                print(f"           Snippet: {textwrap.shorten(snippet, 80)}")
            if ex.get("error_msg"):
                print(f"           Error  : {textwrap.shorten(str(ex['error_msg']), 80)}")
        print()

    print(sep)
    print("  Action: Review the top patterns and update classify_v2.txt accordingly.")
    print(f"  Then run:  python scripts/eval_classify_prompt.py\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and report LangSmith classification misclassifications."
    )
    parser.add_argument("--days",    type=int, default=28,       help="Lookback window in days (default: 28)")
    parser.add_argument("--project", type=str, default="glacex-ai", help="LangSmith project name")
    parser.add_argument("--limit",   type=int, default=500,      help="Max runs to fetch (default: 500)")
    args = parser.parse_args()

    # Resolve API key (support both env var names)
    api_key = (
        os.getenv("LANGSMITH_API_KEY")
        or os.getenv("LANGCHAIN_API_KEY")
    )
    if not api_key:
        print(
            "\n[ERROR] No LangSmith API key found.\n"
            "  Set one of the following environment variables:\n"
            "    LANGSMITH_API_KEY=<your-key>\n"
            "    LANGCHAIN_API_KEY=<your-key>\n"
            "  Or add it to .env.local and re-run.\n"
            "  Get your key at: https://smith.langchain.com/settings\n"
        )
        sys.exit(1)

    try:
        client = Client(api_key=api_key)
        # Quick connectivity check
        _ = client.read_project(project_name=args.project)
    except Exception as exc:
        print(
            f"\n[ERROR] Cannot connect to LangSmith: {exc}\n\n"
            "  Setup instructions:\n"
            "    1. Create an account at https://smith.langchain.com\n"
            "    2. Generate an API key under Settings → API Keys\n"
            "    3. Set LANGSMITH_API_KEY in .env.local\n"
            "    4. Make sure the project 'glacex-ai' exists (or use --project <name>)\n"
            "    5. Enable tracing in your app:  LANGCHAIN_TRACING_V2=true\n"
        )
        sys.exit(1)

    supabase_db_url = os.getenv("SUPABASE_DB_URL")
    feedback_map    = fetch_feedback_map(supabase_db_url)

    runs     = fetch_runs(client, args.project, args.days, args.limit)
    patterns = build_pattern_report(runs, feedback_map)
    print_report(patterns, len(runs), args.days)


if __name__ == "__main__":
    main()
