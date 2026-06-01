#!/usr/bin/env python3
"""
record_feedback.py — Called by the feedback_webhook.yml GitHub Actions workflow.

Receives an article_id and a rating ('good' | 'noise') from the ntfy.sh
action-button webhook and upserts the record into public.user_feedback.

Usage:
    python scripts/record_feedback.py --article-id <UUID> --rating <good|noise>
"""
import argparse
import os
import sys
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Record signal-quality feedback.")
    parser.add_argument("--article-id", required=True, help="UUID of the article being rated.")
    parser.add_argument(
        "--rating",
        required=True,
        choices=["good", "noise"],
        help="Feedback rating: 'good' (relevant signal) or 'noise' (irrelevant).",
    )
    return parser.parse_args()


def main():
    load_dotenv()
    load_dotenv(".env.local")

    args = parse_args()
    article_id = args.article_id.strip()
    rating = args.rating.strip()

    db_url = os.getenv("SUPABASE_DB_URL", "")
    if not db_url:
        logger.error("SUPABASE_DB_URL environment variable is missing.")
        sys.exit(1)

    # Percent-encode spaces in the password (common Supabase credential issue)
    db_url = db_url.replace(" ", "%20")

    try:
        import psycopg2
    except ImportError:
        logger.error("psycopg2 is not installed. Run: uv add psycopg2-binary")
        sys.exit(1)

    logger.info(f"Recording feedback: article_id={article_id!r}  rating={rating!r}")

    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cursor = conn.cursor()

        # Idempotent upsert: one rating per article (last-writer-wins on conflict)
        # If you want to allow multiple ratings per article, change ON CONFLICT to DO NOTHING.
        cursor.execute(
            """
            INSERT INTO public.user_feedback (article_id, rating, rated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT (article_id)
            DO UPDATE SET
                rating    = EXCLUDED.rating,
                rated_at  = EXCLUDED.rated_at
            """,
            (article_id, rating, datetime.now(timezone.utc)),
        )

        cursor.close()
        conn.close()
        logger.info(f"✅ Feedback recorded successfully: {article_id} → {rating}")

    except Exception as exc:
        logger.error(f"Failed to record feedback: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
