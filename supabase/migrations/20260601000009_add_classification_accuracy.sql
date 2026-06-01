-- Migration: add classification_accuracy column to pipeline_runs
-- Tracks the fraction of classifications within ±15 points of human-verified labels.
-- Populated by delivery_agent.py after each run via update_pipeline_run_metric().

ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS classification_accuracy DOUBLE PRECISION DEFAULT NULL;

COMMENT ON COLUMN pipeline_runs.classification_accuracy IS
    'Fraction (0.0–1.0) of Groq/Gemini classifications that fell within ±15 importance '
    'points of the human-verified label in the held-out eval set. NULL if no eval was '
    'run this period. Populated by scripts/eval_classify_prompt.py and stored here via '
    'the delivery_agent at end-of-run.';

-- Add prompt_version column so we can correlate accuracy with which prompt was active.
ALTER TABLE pipeline_runs
    ADD COLUMN IF NOT EXISTS prompt_version TEXT DEFAULT 'classify_v1';

COMMENT ON COLUMN pipeline_runs.prompt_version IS
    'Version of classify_*.txt active during this run (e.g. classify_v1, classify_v2). '
    'Set by llm_agent.py from the CLASSIFY_PROMPT_VERSION env/config value.';
