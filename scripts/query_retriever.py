#!/usr/bin/env python
"""
GlaceX – On‑demand retrieval entry point.

The GitHub Actions workflow `query_retriever.yml` sets the environment variable
`QUERY` to the user‑provided free‑text query. This script forwards that query
to the existing `EnsembleRetriever`, formats the top‑5 results as Markdown,
and writes the output to `/tmp/query_result.md` (read by the ntfy step).

Prerequisites:
- The project's virtual environment is already activated in the CI job.
- `llm.retriever.EnsembleRetriever` can be instantiated with the required
  Supabase credentials (available as environment variables).
"""

import os
import sys
from pathlib import Path

# Add project root to PYTHONPATH so internal imports work
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from llm.retriever import EnsembleRetriever  # type: ignore


def main() -> None:
    query = os.getenv("QUERY")
    if not query:
        print("❌ No QUERY environment variable supplied.", file=sys.stderr)
        sys.exit(1)

    # Initialise the retriever (it reads Supabase config from env)
    retriever = EnsembleRetriever()
    try:
        results = retriever.retrieve(query, top_k=5)
    except Exception as exc:
        print(f"❌ Retrieval failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Build a simple markdown report
    md_lines = [
        f"# GlaceX Query Result",
        f"**Query:** `{query}`",
        "",
        "## Top 5 Articles",
        "",
    ]

    if not results:
        md_lines.append("_No relevant articles found._")
    else:
        for idx, doc in enumerate(results, start=1):
            title = doc.get("title", "Untitled")
            url = doc.get("url", "")
            snippet = doc.get("snippet", "")
            md_lines.append(f"### {idx}. {title}")
            if url:
                md_lines.append(f"[Read article]({url})")
            if snippet:
                md_lines.append(f"> {snippet}")
            md_lines.append("")

    report_path = Path("/tmp/query_result.md")
    report_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"✅ Report written to {report_path}")


if __name__ == "__main__":
    main()
