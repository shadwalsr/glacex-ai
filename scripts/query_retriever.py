#!/usr/bin/env python
"""
GlaceX – On-demand retrieval entry point.

Called by the GitHub Actions workflow `query_retriever.yml`.
Reads the QUERY environment variable, runs the EnsembleRetriever,
and writes a Markdown report to /tmp/query_result.md.
"""

import os
import sys
from pathlib import Path

# Add project root to PYTHONPATH so internal imports work
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env.local", override=True)
load_dotenv(PROJECT_ROOT / ".env", override=True)

from supabase import create_client
from llm.retriever import get_ensemble_retriever


def main() -> None:
    query = os.getenv("QUERY")
    if not query:
        # Also accept as a CLI argument
        if len(sys.argv) > 1:
            query = " ".join(sys.argv[1:])
        else:
            print("❌ No QUERY environment variable or CLI argument supplied.", file=sys.stderr)
            sys.exit(1)

    print(f"🔍 Running query: {query}")

    # Build Supabase client from env
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key:
        print("❌ SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.", file=sys.stderr)
        sys.exit(1)

    client = create_client(supabase_url, supabase_key)

    # Build the ensemble retriever
    try:
        retriever = get_ensemble_retriever(client, match_count=5)
    except Exception as exc:
        print(f"❌ Failed to build retriever: {exc}", file=sys.stderr)
        sys.exit(1)

    # Run the query
    try:
        results = retriever.invoke(query)
    except Exception as exc:
        print(f"❌ Retrieval failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Build a simple markdown report
    md_lines = [
        "# GlaceX Query Result",
        f"**Query:** `{query}`",
        "",
        "## Top 5 Articles",
        "",
    ]

    if not results:
        md_lines.append("_No relevant articles found._")
    else:
        for idx, doc in enumerate(results[:5], start=1):
            title = doc.metadata.get("title", "Untitled")
            url = doc.metadata.get("url", "")
            snippet = doc.page_content[:300].strip()
            md_lines.append(f"### {idx}. {title}")
            if url:
                md_lines.append(f"[Read article]({url})")
            if snippet:
                md_lines.append(f"> {snippet}")
            md_lines.append("")

    report = "\n".join(md_lines)

    # Write to /tmp for the ntfy step, and also print to stdout
    report_path = Path("/tmp/query_result.md")
    report_path.write_text(report, encoding="utf-8")
    print(report)
    print(f"\n✅ Report written to {report_path}")


if __name__ == "__main__":
    main()
