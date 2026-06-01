import pytest
import asyncio
import time
from agents.llm_agent import TokenBucketLimiter, extract_arxiv_sections, validate_and_repair_json, ClassificationResult, InsightResult

@pytest.mark.asyncio
async def test_token_bucket_limiter():
    limiter = TokenBucketLimiter(rate_limit=5/60, capacity=2.0)
    start = time.monotonic()
    await limiter.wait_for_token()
    await limiter.wait_for_token()
    elapsed = time.monotonic() - start
    assert elapsed < 0.1
    
    limiter_fast = TokenBucketLimiter(rate_limit=10.0, capacity=1.0)
    await limiter_fast.wait_for_token()
    
    start_fast = time.monotonic()
    await limiter_fast.wait_for_token()
    elapsed_fast = time.monotonic() - start_fast
    assert elapsed_fast >= 0.08

def test_extract_arxiv_sections_basic():
    text = """
    A Title of the Paper
    
    Abstract
    This is the abstract of the paper. It describes the overall work.
    
    1 Introduction
    This is the introduction. It introduces the problem.
    
    2 Related Work
    This is the related work.
    
    5 Conclusion
    We conclude that this system works well.
    
    References
    [1] Author, A. (2026).
    """
    extracted = extract_arxiv_sections(text)
    assert "--- ABSTRACT ---" in extracted
    assert "This is the abstract" in extracted
    assert "--- INTRODUCTION ---" in extracted
    assert "This is the introduction" in extracted
    assert "--- CONCLUSION ---" in extracted
    assert "We conclude that" in extracted
    assert "Related Work" not in extracted
    assert "References" not in extracted

def test_extract_arxiv_sections_fallback():
    text = "Short text without standard sections."
    extracted = extract_arxiv_sections(text)
    assert extracted == text

def test_validate_and_repair_json_valid_classification():
    raw_json = """{
        "category": "paper",
        "subcategory": "agents",
        "importance": 85,
        "is_ai_relevant": true,
        "technical_depth": "high",
        "entities_mentioned": ["Gemini"],
        "reason": "Test reason"
    }"""
    res, was_repaired, err = validate_and_repair_json(raw_json, ClassificationResult)
    assert res is not None
    assert res.category == "paper"
    assert not was_repaired
    assert err is None

def test_validate_and_repair_json_malformed_but_reparable():
    # Malformed JSON with a trailing comma and unclosed bracket/missing quote
    raw_json = """{
        "category": "tool",
        "subcategory": "agent-framework",
        "importance": 70,
        "is_ai_relevant": true,
        "technical_depth": "medium",
        "entities_mentioned": ["LlamaIndex"],
        "reason": "Trailing comma example",
    }"""
    res, was_repaired, err = validate_and_repair_json(raw_json, ClassificationResult)
    assert res is not None
    assert res.subcategory == "agent-framework"
    assert was_repaired
    assert err is None

def test_validate_and_repair_json_totally_invalid():
    raw_json = "This is not JSON at all."
    res, was_repaired, err = validate_and_repair_json(raw_json, ClassificationResult)
    assert res is None
    assert not was_repaired
    assert err is not None
