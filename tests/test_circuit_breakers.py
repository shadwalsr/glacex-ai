import pytest
import datetime
from unittest.mock import patch, MagicMock, AsyncMock, ANY
from agents.circuit_breaker import PersistentCircuitBreaker, CircuitBreakerOpenException, is_supabase_open
from delivery.ntfy_delivery import send_insight_push
from agents.ingestion_agent import process_rss_source
from agents.llm_agent import run_groq_classification

# Create a clean, mock state database helper
def get_mock_db_state(state="closed", failure_count=0, reset_at=None):
    return {
        "service_name": "test_service",
        "state": state,
        "failure_count": failure_count,
        "last_failure_at": None,
        "reset_at": reset_at
    }

@patch("agents.circuit_breaker.PersistentCircuitBreaker.fetch_state")
@patch("agents.circuit_breaker.PersistentCircuitBreaker.update_state")
def test_circuit_breaker_retries_and_opens(mock_update, mock_fetch):
    # Set initial state to closed, with 2 failures already
    mock_fetch.return_value = get_mock_db_state(state="closed", failure_count=2)
    
    breaker = PersistentCircuitBreaker("test_service")
    call_count = 0
    
    def failing_func():
        nonlocal call_count
        call_count += 1
        raise ValueError("Network error")
        
    with pytest.raises(ValueError):
        breaker.call(failing_func)
        
    # Tenacity should retry 3 times (attempt 1, 2, 3) inside breaker.call
    assert call_count == 3
    # Check that it updated state with failure count and opened the circuit (since 2+1=3 >= 3)
    mock_update.assert_any_call("open", 3, ANY, ANY)

@patch("agents.circuit_breaker.PersistentCircuitBreaker.fetch_state")
def test_circuit_breaker_bypasses_when_open(mock_fetch):
    # Circuit is open
    future_reset = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)).isoformat()
    mock_fetch.return_value = get_mock_db_state(state="open", failure_count=3, reset_at=future_reset)
    
    breaker = PersistentCircuitBreaker("test_service")
    dummy = MagicMock()
    
    with pytest.raises(CircuitBreakerOpenException):
        breaker.call(dummy)
        
    dummy.assert_not_called()

@patch("agents.circuit_breaker.PersistentCircuitBreaker.fetch_state")
@patch("agents.circuit_breaker.PersistentCircuitBreaker.update_state")
def test_circuit_breaker_transitions_half_open(mock_update, mock_fetch):
    # Reset time is in the past, so should transition to half-open
    past_reset = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)).isoformat()
    mock_fetch.return_value = get_mock_db_state(state="open", failure_count=3, reset_at=past_reset)
    
    breaker = PersistentCircuitBreaker("test_service")
    dummy = MagicMock(return_value="success")
    
    res = breaker.call(dummy)
    assert res == "success"
    # Verify transition to half-open and then closed
    mock_update.assert_any_call("half-open", 3)
    mock_update.assert_any_call("closed", 0, None, None)

@patch("agents.circuit_breaker.PersistentCircuitBreaker.fetch_state")
def test_is_supabase_open(mock_fetch):
    mock_fetch.return_value = get_mock_db_state(state="open")
    assert is_supabase_open() is True
    
    mock_fetch.return_value = get_mock_db_state(state="closed")
    assert is_supabase_open() is False

@patch("agents.llm_agent.groq_client")
@patch("agents.llm_agent.supabase")
@patch("agents.llm_agent.genai.GenerativeModel")
@patch("agents.circuit_breaker.PersistentCircuitBreaker.fetch_state")
@patch("agents.circuit_breaker.PersistentCircuitBreaker.update_state")
def test_groq_fallback_to_gemini(mock_update, mock_fetch, mock_gemini_model, mock_supabase, mock_groq_client):
    # Setup mock articles to classify
    mock_supabase.table.return_value.select.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[
        {"id": "art-1", "title": "Test Title", "clean_text": "Clean Text", "url": "http://example.com", "raw_html": "HTML", "published_at": None, "source_id": "src-1"}
    ])
    
    # Mock Groq to fail consistently
    mock_groq_client.chat.completions.create.side_effect = Exception("Groq Rate Limit")
    
    # Mock Gemini fallback to succeed
    mock_response = MagicMock()
    mock_response.text = '{"category": "tool", "subcategory": "LLM", "importance": 85, "is_ai_relevant": true, "technical_depth": "high", "entities_mentioned": [], "reason": "test"}'
    
    mock_gemini_instance = MagicMock()
    mock_gemini_instance.generate_content_async = AsyncMock(return_value=mock_response)
    mock_gemini_model.return_value = mock_gemini_instance
    
    # Mock circuit breaker state
    mock_fetch.return_value = get_mock_db_state(state="closed", failure_count=0)
    
    count = run_groq_classification()
    
    # Check that 1 article was classified successfully via fallback
    assert count == 1
    assert mock_groq_client.chat.completions.create.call_count == 3  # retries 3 times due to circuit breaker/tenacity
    mock_gemini_instance.generate_content_async.assert_called_once()

@patch("delivery.ntfy_delivery.httpx.post")
@patch("agents.circuit_breaker.PersistentCircuitBreaker.fetch_state")
def test_ntfy_circuit_breaker_bypasses(mock_fetch, mock_post):
    # Mock ntfy circuit breaker as open
    future_reset = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)).isoformat()
    mock_fetch.return_value = get_mock_db_state(state="open", failure_count=3, reset_at=future_reset)
    
    # Should bypass posting to ntfy
    res = send_insight_push("Headline", "Message", "http://example.com", "tool", 3)
    
    assert res is False
    mock_post.assert_not_called()

@pytest.mark.asyncio
@patch("agents.ingestion_agent.scrape_rss")
@patch("agents.circuit_breaker.PersistentCircuitBreaker.fetch_state")
async def test_scraper_site_circuit_breaker_bypasses(mock_fetch, mock_scrape_rss):
    # Mock domain-level scraper circuit breaker as open
    future_reset = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=30)).isoformat()
    mock_fetch.return_value = get_mock_db_state(state="open", failure_count=3, reset_at=future_reset)
    
    source = {
        "id": "src-1",
        "name": "Failing Blog",
        "url": "http://failingblog.com/feed",
        "type": "rss"
    }
    
    articles, success = await process_rss_source(source)
    
    assert success is False
    assert articles == []
    mock_scrape_rss.assert_not_called()
