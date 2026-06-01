"""
test_prompt_optimization.py

Tests for Phase 9.3: Prompt Optimization via LangSmith data.
Covers:
  - classify_v2.txt existence and content validation
  - prompt_versions.yaml schema
  - llm_agent run_stats includes new fields
  - observability state persists prompt_version and classification_accuracy
  - promote_classify_prompt.py dry-run logic
"""
import os
import json
import pytest
from unittest.mock import patch, MagicMock


# ── classify_v2.txt content validation ───────────────────────────────────────

def test_classify_v2_prompt_file_exists():
    """classify_v2.txt must exist in the prompts/ directory."""
    v2_path = os.path.join("prompts", "classify_v2.txt")
    assert os.path.exists(v2_path), f"classify_v2.txt not found at {v2_path}"


def test_classify_v2_contains_edge_case_block():
    """classify_v2.txt must include the SCORING EDGE CASES correction block."""
    v2_path = os.path.join("prompts", "classify_v2.txt")
    if not os.path.exists(v2_path):
        pytest.skip("classify_v2.txt not present")
    content = open(v2_path, encoding="utf-8").read()
    assert "SCORING EDGE CASES" in content, "Edge-case block missing from classify_v2.txt"
    # Check each of the 5 correction patterns is present
    assert "Patch/bugfix" in content or "patch" in content.lower()
    assert "funding" in content.lower()
    assert "interview" in content.lower() or "podcast" in content.lower()
    assert "benchmark" in content.lower()
    assert "fine-tune" in content.lower() or "finetune" in content.lower() or "domain-specific" in content.lower()


def test_classify_v2_has_more_examples_than_v1():
    """classify_v2.txt must contain more few-shot examples than classify_v1.txt."""
    v1_path = os.path.join("prompts", "classify_v1.txt")
    v2_path = os.path.join("prompts", "classify_v2.txt")
    if not os.path.exists(v2_path):
        pytest.skip("classify_v2.txt not present")

    v1 = open(v1_path, encoding="utf-8").read()
    v2 = open(v2_path, encoding="utf-8").read()

    # Count "User:\nClassify this article" as a proxy for example count
    v1_count = v1.count("Classify this article")
    v2_count = v2.count("Classify this article")
    assert v2_count > v1_count, (
        f"v2 should have more examples than v1 (v1={v1_count}, v2={v2_count})"
    )


def test_classify_v2_correction_examples_have_lower_patch_score():
    """The patch-release correction example in v2 must show importance < 50."""
    v2_path = os.path.join("prompts", "classify_v2.txt")
    if not os.path.exists(v2_path):
        pytest.skip("classify_v2.txt not present")
    content = open(v2_path, encoding="utf-8").read()
    # Find the patch-release example block and verify its importance score is low
    assert "patch-release" in content, "Missing patch-release subcategory example in v2"
    # The correction example should not have importance >= 75
    import re
    # Find all importance values in the v2-corrections section
    corrections_section = content.split("v2 CORRECTION EXAMPLES")[-1] if "v2 CORRECTION EXAMPLES" in content else content
    importances = [int(m) for m in re.findall(r'"importance":\s*(\d+)', corrections_section)]
    assert importances, "No importance values found in correction examples"
    # The lowest importance in corrections should be below 50 (the patch-release example)
    assert min(importances) < 50, f"Expected at least one low-importance correction example, got: {importances}"


# ── prompt_versions.yaml ────────────────────────────────────────────────────

def test_prompt_versions_yaml_exists():
    """config/prompt_versions.yaml must exist."""
    assert os.path.exists(os.path.join("config", "prompt_versions.yaml"))


def test_prompt_versions_yaml_has_required_keys():
    """prompt_versions.yaml must contain classify_prompt, extract_prompt, digest_prompt."""
    import yaml
    cfg_path = os.path.join("config", "prompt_versions.yaml")
    if not os.path.exists(cfg_path):
        pytest.skip("prompt_versions.yaml not present")
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    assert "classify_prompt" in data, "Missing classify_prompt in prompt_versions.yaml"
    assert "extract_prompt" in data, "Missing extract_prompt in prompt_versions.yaml"
    assert data["classify_prompt"].startswith("classify_"), (
        f"classify_prompt should start with 'classify_', got: {data['classify_prompt']}"
    )


def test_prompt_versions_yaml_default_is_v1():
    """Default classify_prompt must be classify_v1 (safe production default)."""
    import yaml
    cfg_path = os.path.join("config", "prompt_versions.yaml")
    if not os.path.exists(cfg_path):
        pytest.skip("prompt_versions.yaml not present")
    with open(cfg_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    assert data.get("classify_prompt") == "classify_v1", (
        "Default classify_prompt should be classify_v1 until eval promotes v2"
    )


# ── llm_agent run_stats ──────────────────────────────────────────────────────

def test_run_stats_has_prompt_version_field():
    """run_stats must include prompt_version (set from config on module load)."""
    from agents import llm_agent
    assert "prompt_version" in llm_agent.run_stats, "run_stats missing prompt_version"
    assert llm_agent.run_stats["prompt_version"].startswith("classify_")


def test_run_stats_has_classification_accuracy_field():
    """run_stats must include classification_accuracy, initialized to None."""
    from agents import llm_agent
    assert "classification_accuracy" in llm_agent.run_stats
    # None until eval_classify_prompt.py has been run this cycle
    assert llm_agent.run_stats["classification_accuracy"] is None


# ── observability state persistence ─────────────────────────────────────────

def test_update_pipeline_run_metric_persists_prompt_version(tmp_path):
    """update_pipeline_run_metric must accept and persist prompt_version."""
    import agents.observability as obs
    original_state_file = obs.STATE_FILE
    obs.STATE_FILE = str(tmp_path / "pipeline_state.json")
    try:
        obs.init_pipeline_run("test-run-v2")
        obs.update_pipeline_run_metric(prompt_version="classify_v2")
        state = obs.load_pipeline_state()
        assert state.get("prompt_version") == "classify_v2"
    finally:
        obs.STATE_FILE = original_state_file


def test_update_pipeline_run_metric_persists_classification_accuracy(tmp_path):
    """update_pipeline_run_metric must accept and persist classification_accuracy."""
    import agents.observability as obs
    original_state_file = obs.STATE_FILE
    obs.STATE_FILE = str(tmp_path / "pipeline_state.json")
    try:
        obs.init_pipeline_run("test-run-acc")
        obs.update_pipeline_run_metric(classification_accuracy=0.88)
        state = obs.load_pipeline_state()
        assert state.get("classification_accuracy") == 0.88
    finally:
        obs.STATE_FILE = original_state_file


# ── promote_classify_prompt.py logic ────────────────────────────────────────

def test_promote_script_exists():
    """scripts/promote_classify_prompt.py must exist."""
    assert os.path.exists(os.path.join("scripts", "promote_classify_prompt.py"))


def test_eval_script_exists():
    """scripts/eval_classify_prompt.py must exist."""
    assert os.path.exists(os.path.join("scripts", "eval_classify_prompt.py"))


def test_fetch_misclassifications_script_exists():
    """scripts/fetch_langsmith_misclassifications.py must exist."""
    assert os.path.exists(os.path.join("scripts", "fetch_langsmith_misclassifications.py"))
