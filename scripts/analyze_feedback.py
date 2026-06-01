#!/usr/bin/env python3
"""
analyze_feedback.py — Monthly KPI report for signal quality feedback loop.

Reads the user_feedback table (populated by ntfy.sh action buttons via GitHub
Actions webhook) and computes precision metrics.

KPI target: precision (good / total_rated) >= 75 %
Alert threshold: precision < 70 % → recommend lowering classification threshold
                                     or refining prompts.

Usage:
    python scripts/analyze_feedback.py [--months N] [--json]

Options:
    --months N   Analyse the last N calendar months (default: 1)
    --json       Output results as machine-readable JSON (useful for CI checks)
    --fail       Exit with code 1 if precision is below the alert threshold (CI mode)
"""
import argparse
import json
import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── Precision thresholds ────────────────────────────────────────────────────
KPI_TARGET_PCT = 75.0   # "good" as % of all rated — GREEN
ALERT_PCT      = 70.0   # below this → trigger alert & recommendations — RED


def parse_args():
    parser = argparse.ArgumentParser(description="Analyze signal quality feedback.")
    parser.add_argument("--months", type=int, default=1,
                        help="Number of past calendar months to analyse (default: 1).")
    parser.add_argument("--json", action="store_true",
                        help="Emit machine-readable JSON output.")
    parser.add_argument("--fail", action="store_true",
                        help="Exit with code 1 if precision is below the alert threshold.")
    return parser.parse_args()


def connect(db_url: str):
    try:
        import psycopg2
        return psycopg2.connect(db_url)
    except ImportError:
        logger.error("psycopg2 is not installed. Run: uv add psycopg2-binary")
        sys.exit(1)
    except Exception as exc:
        logger.error(f"Database connection failed: {exc}")
        sys.exit(1)


def analyse(cursor, since: datetime) -> dict:
    """Return precision metrics for feedback submitted after `since`."""

    # ── Overall counts ───────────────────────────────────────────────────────
    cursor.execute(
        """
        SELECT rating, COUNT(*) AS cnt
        FROM public.user_feedback
        WHERE rated_at >= %s
        GROUP BY rating
        """,
        (since,),
    )
    counts = {row[0]: int(row[1]) for row in cursor.fetchall()}
    good  = counts.get("good", 0)
    noise = counts.get("noise", 0)
    total = good + noise

    precision = (good / total * 100.0) if total > 0 else None

    # ── Weekly breakdown ─────────────────────────────────────────────────────
    cursor.execute(
        """
        SELECT
            date_trunc('week', rated_at) AS week_start,
            rating,
            COUNT(*) AS cnt
        FROM public.user_feedback
        WHERE rated_at >= %s
        GROUP BY week_start, rating
        ORDER BY week_start
        """,
        (since,),
    )
    weekly_raw: dict[str, dict] = {}
    for row in cursor.fetchall():
        week_key = row[0].strftime("%Y-%m-%d")
        rating   = row[1]
        cnt      = int(row[2])
        if week_key not in weekly_raw:
            weekly_raw[week_key] = {"good": 0, "noise": 0}
        weekly_raw[week_key][rating] = cnt

    weekly = []
    for week, data in sorted(weekly_raw.items()):
        w_good  = data["good"]
        w_noise = data["noise"]
        w_total = w_good + w_noise
        w_prec  = (w_good / w_total * 100.0) if w_total > 0 else None
        weekly.append({"week_start": week, "good": w_good, "noise": w_noise,
                       "total": w_total, "precision_pct": w_prec})

    # ── Worst performing articles ────────────────────────────────────────────
    cursor.execute(
        """
        SELECT uf.article_id, a.url, uf.rating, uf.rated_at
        FROM public.user_feedback uf
        LEFT JOIN public.articles a ON a.id = uf.article_id
        WHERE uf.rated_at >= %s AND uf.rating = 'noise'
        ORDER BY uf.rated_at DESC
        LIMIT 20
        """,
        (since,),
    )
    noise_articles = [
        {"article_id": str(r[0]), "url": r[1], "rated_at": r[3].isoformat()}
        for r in cursor.fetchall()
    ]

    return {
        "since": since.isoformat(),
        "good":  good,
        "noise": noise,
        "total": total,
        "precision_pct": precision,
        "weekly_breakdown": weekly,
        "noise_articles": noise_articles,
    }


def recommendations(precision: float | None) -> list[str]:
    """Return actionable recommendations based on precision value."""
    if precision is None:
        return ["No feedback data yet. Encourage users to tap Good Signal / Noise buttons."]

    recs = []
    if precision < ALERT_PCT:
        recs.append(
            f"🚨 Precision {precision:.1f}% is below the {ALERT_PCT}% alert threshold."
        )
        recs.append(
            "→ Lower the LLM classification threshold in config/notification_settings.yaml "
            "(try reducing high_threshold from 85 → 80)."
        )
        recs.append(
            "→ Review the 20 noise articles above and add representative few-shot "
            "negative examples to prompts/classify_v1.txt."
        )
        recs.append(
            "→ After updating, deploy classify_v2.txt and track accuracy for 2 weeks."
        )
    elif precision < KPI_TARGET_PCT:
        recs.append(
            f"⚠️  Precision {precision:.1f}% is below the KPI target of {KPI_TARGET_PCT}%."
        )
        recs.append(
            "→ Review noise articles and consider adding 2-3 new few-shot examples."
        )
        recs.append(
            "→ No immediate threshold change required; monitor for another week."
        )
    else:
        recs.append(
            f"✅ Precision {precision:.1f}% meets or exceeds the {KPI_TARGET_PCT}% KPI target."
        )
        recs.append("→ No action required. Continue monitoring monthly.")

    return recs


def print_report(result: dict, recs: list[str], months: int) -> None:
    prec = result["precision_pct"]
    prec_str = f"{prec:.1f}%" if prec is not None else "N/A (no data)"

    print()
    print("=" * 60)
    print(f"  Glacex.ai Signal Quality KPI — Last {months} Month(s)")
    print("=" * 60)
    print(f"  Period start    : {result['since'][:10]}")
    print(f"  Good signals    : {result['good']}")
    print(f"  Noise ratings   : {result['noise']}")
    print(f"  Total feedback  : {result['total']}")
    print(f"  Precision       : {prec_str}")
    print(f"  KPI target      : >= {KPI_TARGET_PCT}%")
    print()

    # Weekly breakdown
    if result["weekly_breakdown"]:
        print("  Weekly breakdown:")
        for w in result["weekly_breakdown"]:
            wp = f"{w['precision_pct']:.0f}%" if w["precision_pct"] is not None else "—"
            print(f"    {w['week_start']}  good={w['good']}  noise={w['noise']}  precision={wp}")
        print()

    # Noise articles sample
    if result["noise_articles"]:
        print(f"  Most recent noise articles ({len(result['noise_articles'])} shown):")
        for art in result["noise_articles"][:5]:
            url = (art["url"] or "unknown")[:80]
            print(f"    • {art['rated_at'][:10]}  {url}")
        print()

    print("  Recommendations:")
    for r in recs:
        print(f"    {r}")
    print("=" * 60)
    print()


def main():
    load_dotenv()
    load_dotenv(".env.local")

    args = parse_args()

    db_url = os.getenv("SUPABASE_DB_URL", "")
    if not db_url:
        logger.error("SUPABASE_DB_URL environment variable is missing.")
        sys.exit(1)
    db_url = db_url.replace(" ", "%20")

    # Compute "since" date: beginning of the earliest month in the window
    now   = datetime.now(timezone.utc)
    since = (now - timedelta(days=30 * args.months)).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    conn   = connect(db_url)
    cursor = conn.cursor()

    try:
        result = analyse(cursor, since)
    finally:
        cursor.close()
        conn.close()

    recs       = recommendations(result["precision_pct"])
    below_alert = (
        result["precision_pct"] is not None
        and result["precision_pct"] < ALERT_PCT
    )

    if args.json:
        payload = {**result, "recommendations": recs, "below_alert_threshold": below_alert}
        print(json.dumps(payload, indent=2, default=str))
    else:
        print_report(result, recs, args.months)

    if args.fail and below_alert:
        sys.exit(1)


if __name__ == "__main__":
    main()
