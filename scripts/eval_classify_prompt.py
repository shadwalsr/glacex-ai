"""
eval_classify_prompt.py

Regression evaluation comparing classify_v1.txt vs classify_v2.txt against a
held-out, human-verified evaluation set drawn from Supabase.

Usage:
    python scripts/eval_classify_prompt.py \\
        [--v1 prompts/classify_v1.txt] \\
        [--v2 prompts/classify_v2.txt] \\
        [--limit 50] \\
        [--output-json /tmp/eval_result.json]

Exit codes:
    0  — v2 accuracy >= v1 accuracy  (or eval set too small, or dry-run)
    1  — v2 accuracy <  v1 accuracy
"""

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# .env.local
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    load_dotenv(".env.local")
except ImportError:
    print("[WARN] python-dotenv not installed; skipping .env.local load.")

# ---------------------------------------------------------------------------
# Optional imports
# ---------------------------------------------------------------------------
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    psycopg2 = None  # type: ignore

try:
    from groq import Groq
except ImportError:
    print(
        "\n[ERROR] 'groq' package not installed.\n"
        "  Install it with:  pip install groq\n"
        "  or:               uv add groq\n"
    )
    sys.exit(1)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GROQ_MODEL          = "llama-3.3-70b-versatile"
TEXT_SNIPPET_CHARS  = 800
IMPORTANCE_THRESHOLD = 60   # same threshold used in the pipeline


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------

@dataclass
class EvalArticle:
    article_id: str
    title: str
    text_snippet: str
    feedback: str                    # 'good' or 'noise'
    correct_category: Optional[str] = None


@dataclass
class PromptResult:
    prompt_name: str
    correct:        int = 0
    incorrect:      int = 0
    false_positives: int = 0   # noise feedback but score >= threshold
    false_negatives: int = 0   # good feedback but score < threshold
    category_correct:   int = 0
    category_evaluated: int = 0
    errors:         int = 0

    @property
    def total(self) -> int:
        return self.correct + self.incorrect

    @property
    def accuracy(self) -> float:
        return self.correct / self.total if self.total else 0.0

    @property
    def false_positive_rate(self) -> float:
        noise_total = self.false_positives + (
            self.correct if self.false_negatives == 0 else 0
        )
        # FPR = FP / (FP + TN);  approximate with FP / total_noise_articles
        total_neg = self.false_positives + (self.correct - self.false_negatives)
        return self.false_positives / total_neg if total_neg else 0.0

    @property
    def false_negative_rate(self) -> float:
        total_pos = self.false_negatives + (self.correct - self.false_positives)
        return self.false_negatives / total_pos if total_pos else 0.0


# ---------------------------------------------------------------------------
# Supabase: fetch eval set
# ---------------------------------------------------------------------------

def fetch_eval_set(limit: int) -> list[EvalArticle]:
    """
    Fetch articles that have BOTH a classification AND a user_feedback entry.
    These form the 'human-verified' evaluation set.
    """
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not supabase_url or not supabase_key:
        print("[ERROR] SUPABASE_URL or SUPABASE_SERVICE_KEY environment variable is not set.")
        sys.exit(1)

    from supabase import create_client
    try:
        supabase = create_client(supabase_url, supabase_key)
        
        # 1. Fetch user feedback
        res_fb = (
            supabase.table("user_feedback")
            .select("article_id, rating")
            .in_("rating", ["good", "noise"])
            .order("rated_at", desc=True)
            .limit(limit)
            .execute()
        )
        feedbacks = res_fb.data or []
        if not feedbacks:
            return []

        article_ids = [f["article_id"] for f in feedbacks]

        # 2. Fetch corresponding articles
        res_art = (
            supabase.table("articles")
            .select("id, title, clean_text")
            .in_("id", article_ids)
            .execute()
        )
        articles_map = {a["id"]: a for a in (res_art.data or [])}

        # 3. Fetch corresponding classifications
        res_cl = (
            supabase.table("classifications")
            .select("article_id, importance")
            .in_("article_id", article_ids)
            .not_.is_("importance", "null")
            .execute()
        )
        class_map = {c["article_id"]: c for c in (res_cl.data or [])}

    except Exception as exc:
        print(f"[ERROR] Failed to fetch eval set from Supabase: {exc}")
        sys.exit(1)

    articles = []
    for f in feedbacks:
        art_id = f["article_id"]
        if art_id in articles_map and art_id in class_map:
            art = articles_map[art_id]
            text = art.get("clean_text") or ""
            articles.append(EvalArticle(
                article_id      = art_id,
                title           = art.get("title") or "",
                text_snippet    = text[:TEXT_SNIPPET_CHARS],
                feedback        = f["rating"],
                correct_category= None,
            ))

    print(f"[INFO] Eval set size: {len(articles)} articles.")
    return articles


# ---------------------------------------------------------------------------
# LLM call
# ---------------------------------------------------------------------------

def call_llm(client: Groq, prompt_text: str, article: EvalArticle) -> dict:
    """
    Run one article through the Groq LLM using the given prompt template.
    Returns a dict with at least 'importance' and optionally 'category'.
    Returns {'error': <msg>} on failure.
    """
    user_content = (
        f"Title: {article.title}\n\n"
        f"Text:\n{article.text_snippet}"
    )

    messages = [
        {"role": "system", "content": prompt_text},
        {"role": "user",   "content": user_content},
    ]

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0.0,
            max_tokens=256,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        result  = json.loads(content)
        return result
    except json.JSONDecodeError as exc:
        return {"error": f"JSON parse error: {exc}", "raw": content}
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Evaluation loop
# ---------------------------------------------------------------------------

def evaluate_prompt(
    client:      Groq,
    prompt_path: Path,
    eval_set:    list[EvalArticle],
    rate_limit_rps: float = 1.0,
) -> PromptResult:
    """Run all eval articles through one prompt and tally results."""
    prompt_text = prompt_path.read_text(encoding="utf-8")
    result      = PromptResult(prompt_name=prompt_path.stem)
    delay       = 1.0 / rate_limit_rps

    for i, article in enumerate(eval_set, start=1):
        print(f"  [{result.prompt_name}] {i}/{len(eval_set)} — {article.title[:60]!r}", end="\r")
        llm_out = call_llm(client, prompt_text, article)

        if "error" in llm_out:
            result.errors += 1
            result.incorrect += 1
            time.sleep(delay)
            continue

        try:
            importance = float(llm_out.get("importance", -1))
        except (TypeError, ValueError):
            result.errors += 1
            result.incorrect += 1
            time.sleep(delay)
            continue

        # Correctness check
        is_correct = False
        if article.feedback == "good"  and importance >= IMPORTANCE_THRESHOLD:
            is_correct = True
        elif article.feedback == "noise" and importance < IMPORTANCE_THRESHOLD:
            is_correct = True
        elif article.feedback == "good"  and importance < IMPORTANCE_THRESHOLD:
            result.false_negatives += 1
        elif article.feedback == "noise" and importance >= IMPORTANCE_THRESHOLD:
            result.false_positives += 1

        if is_correct:
            result.correct += 1
        else:
            result.incorrect += 1

        # Category check (optional)
        if article.correct_category:
            result.category_evaluated += 1
            llm_cat = (llm_out.get("category") or "").strip().lower()
            if llm_cat == article.correct_category.strip().lower():
                result.category_correct += 1

        time.sleep(delay)

    print()  # newline after \r
    return result


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

SEPARATOR = "-" * 72

def print_comparison_table(v1: PromptResult, v2: PromptResult) -> None:
    """Print a side-by-side comparison of prompt evaluation results."""
    header = f"{'Metric':<28} {'classify_v1':>12} {'classify_v2':>12}"
    print(f"\n{SEPARATOR}")
    print("  GlaceX Prompt Evaluation — Comparison Table")
    print(f"{SEPARATOR}")
    print(f"  {header}")
    print(f"  {'-'*28} {'-'*12} {'-'*12}")

    rows = [
        ("Total articles",         v1.total,                   v2.total),
        ("Correct",                v1.correct,                 v2.correct),
        ("Incorrect",              v1.incorrect,               v2.incorrect),
        ("Errors (LLM/parse)",     v1.errors,                  v2.errors),
        ("False Positives",        v1.false_positives,         v2.false_positives),
        ("False Negatives",        v1.false_negatives,         v2.false_negatives),
        ("Accuracy",               f"{v1.accuracy*100:.1f}%",  f"{v2.accuracy*100:.1f}%"),
        ("False Positive Rate",    f"{v1.false_positive_rate*100:.1f}%", f"{v2.false_positive_rate*100:.1f}%"),
        ("False Negative Rate",    f"{v1.false_negative_rate*100:.1f}%", f"{v2.false_negative_rate*100:.1f}%"),
    ]
    if v1.category_evaluated > 0 or v2.category_evaluated > 0:
        cat_v1 = (
            f"{v1.category_correct}/{v1.category_evaluated} "
            f"({100*v1.category_correct/v1.category_evaluated:.1f}%)"
            if v1.category_evaluated else "n/a"
        )
        cat_v2 = (
            f"{v2.category_correct}/{v2.category_evaluated} "
            f"({100*v2.category_correct/v2.category_evaluated:.1f}%)"
            if v2.category_evaluated else "n/a"
        )
        rows.append(("Category accuracy", cat_v1, cat_v2))

    for label, val1, val2 in rows:
        print(f"  {label:<28} {str(val1):>12} {str(val2):>12}")

    delta = v2.accuracy - v1.accuracy
    delta_str = f"{'+' if delta >= 0 else ''}{delta*100:.1f}%"
    verdict = "✅ v2 is better or equal" if delta >= 0 else "❌ v2 is WORSE"
    print(f"\n  Accuracy delta (v2 − v1): {delta_str}  →  {verdict}")
    print(f"{SEPARATOR}\n")


def build_json_output(v1: PromptResult, v2: PromptResult) -> dict:
    return {
        "v1_accuracy":          v1.accuracy,
        "v2_accuracy":          v2.accuracy,
        "accuracy_delta":       v2.accuracy - v1.accuracy,
        "v2_better_or_equal":   v2.accuracy >= v1.accuracy,
        "v1": asdict(v1),
        "v2": asdict(v2),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate classify prompt v1 vs v2 on human-verified eval set."
    )
    parser.add_argument("--v1",          default="prompts/classify_v1.txt",
                        help="Path to v1 prompt (default: prompts/classify_v1.txt)")
    parser.add_argument("--v2",          default="prompts/classify_v2.txt",
                        help="Path to v2 prompt (default: prompts/classify_v2.txt)")
    parser.add_argument("--limit",       type=int, default=50,
                        help="Max eval set size (default: 50)")
    parser.add_argument("--output-json", default=None,
                        help="Path to write JSON results (optional)")
    args = parser.parse_args()

    v1_path = Path(args.v1)
    v2_path = Path(args.v2)

    # Validate prompt files
    for p in (v1_path, v2_path):
        if not p.exists():
            print(f"[ERROR] Prompt file not found: {p}")
            sys.exit(1)

    # Fetch eval set
    eval_set = fetch_eval_set(args.limit)

    if len(eval_set) < 5:
        print(
            f"\n[WARN] Eval set has only {len(eval_set)} articles (need >= 5).\n"
            "  Not enough human-verified data yet. Collect more feedback first.\n"
            "  Exiting with code 0 (no regression detected)."
        )
        sys.exit(0)

    # Groq client
    groq_api_key = os.getenv("GROQ_API_KEY")
    if not groq_api_key:
        print("[ERROR] GROQ_API_KEY environment variable is not set.")
        sys.exit(1)

    groq_client = Groq(api_key=groq_api_key)

    print(f"\n[INFO] Evaluating '{v1_path.stem}' …")
    result_v1 = evaluate_prompt(groq_client, v1_path, eval_set)

    print(f"[INFO] Evaluating '{v2_path.stem}' …")
    result_v2 = evaluate_prompt(groq_client, v2_path, eval_set)

    print_comparison_table(result_v1, result_v2)

    # Write JSON output
    if args.output_json:
        out = build_json_output(result_v1, result_v2)
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output_json).write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"[INFO] JSON results written to: {args.output_json}")

    # Exit code
    if result_v2.accuracy >= result_v1.accuracy:
        print("[INFO] ✅ v2 accuracy >= v1 accuracy — no regression. Exiting 0.")
        sys.exit(0)
    else:
        print("[WARN] ❌ v2 accuracy < v1 accuracy — regression detected! Exiting 1.")
        sys.exit(1)


if __name__ == "__main__":
    main()
