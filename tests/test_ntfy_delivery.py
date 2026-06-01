import pytest
import respx
import httpx
import os
import re
import datetime
from unittest.mock import patch, MagicMock
from delivery.ntfy_delivery import (
    map_importance_to_priority,
    deliver_pending_insights,
    check_quiet_hours,
    load_notification_settings,
    send_insight_push,
)

def test_map_importance_to_priority():
    # Test 1-10 scale
    assert map_importance_to_priority(9) == 5
    assert map_importance_to_priority(7.5) == 4
    assert map_importance_to_priority(5) == 3
    assert map_importance_to_priority(3.5) == 2
    assert map_importance_to_priority(1.5) == 1
    
    # Test 0-100 scale
    assert map_importance_to_priority(95) == 5
    assert map_importance_to_priority(75) == 4
    assert map_importance_to_priority(55) == 3
    assert map_importance_to_priority(35) == 2
    assert map_importance_to_priority(15) == 1
    
    # Defaults/errors
    assert map_importance_to_priority(None) == 3
    assert map_importance_to_priority("invalid") == 3

def test_check_quiet_hours():
    # Simple quiet hours (no midnight crossing)
    assert check_quiet_hours(3, 2, 6) is True
    assert check_quiet_hours(1, 2, 6) is False
    assert check_quiet_hours(6, 2, 6) is False
    
    # Midnight crossing quiet hours
    assert check_quiet_hours(23, 22, 6) is True
    assert check_quiet_hours(1, 22, 6) is True
    assert check_quiet_hours(21, 22, 6) is False
    assert check_quiet_hours(6, 22, 6) is False

def test_load_notification_settings():
    settings = load_notification_settings()
    assert "high_threshold" in settings
    assert "digest_threshold" in settings
    assert "max_per_run" in settings
    assert "quiet_hours" in settings

@respx.mock
def test_deliver_pending_insights_fatigue_prevention_flow():
    # Mock ntfy.sh POST route using re.compile
    ntfy_route = respx.post(url=re.compile(r"https://ntfy.sh/.*")).respond(status_code=200, text="ok")
    
    # Set up mock Supabase client data
    mock_del_res = MagicMock()
    mock_del_res.data = []  # no delivered items
    
    mock_ins_res = MagicMock()
    mock_ins_res.data = [
        {"id": "ins-1", "headline": "Headline 0 (score 90)", "tldr": ["bullet 1"], "category": "tool", "article_id": "art-1"},
        {"id": "ins-2", "headline": "Headline 1 (score 88)", "tldr": ["bullet 2"], "category": "tool", "article_id": "art-2"},
        {"id": "ins-3", "headline": "Headline 2 (score 75)", "tldr": ["bullet 3"], "category": "tool", "article_id": "art-3"},
        {"id": "ins-4", "headline": "Headline 3 (score 70)", "tldr": ["bullet 4"], "category": "tool", "article_id": "art-4"},
        {"id": "ins-5", "headline": "Headline 4 (score 50)", "tldr": ["bullet 5"], "category": "tool", "article_id": "art-5"},
        {"id": "ins-6", "headline": "Headline 5 (score 40)", "tldr": ["bullet 6"], "category": "tool", "article_id": "art-6"},
    ]
    
    mock_art_res = MagicMock()
    mock_art_res.data = [
        {"id": "art-1", "url": "http://test.com/1"},
        {"id": "art-2", "url": "http://test.com/2"},
        {"id": "art-3", "url": "http://test.com/3"},
        {"id": "art-4", "url": "http://test.com/4"},
        {"id": "art-5", "url": "http://test.com/5"},
        {"id": "art-6", "url": "http://test.com/6"},
    ]
    
    mock_cls_res = MagicMock()
    mock_cls_res.data = [
        {"article_id": "art-1", "importance": 90},
        {"article_id": "art-2", "importance": 88},
        {"article_id": "art-3", "importance": 75},
        {"article_id": "art-4", "importance": 70},
        {"article_id": "art-5", "importance": 50},
        {"article_id": "art-6", "importance": 40},
    ]

    mock_deliveries_query = MagicMock()
    mock_deliveries_query.select.return_value.eq.return_value.execute.return_value = mock_del_res
    mock_deliveries_query.insert.return_value.execute.return_value = MagicMock()

    mock_insights_query = MagicMock()
    mock_insights_query.select.return_value.execute.return_value = mock_ins_res

    mock_articles_query = MagicMock()
    mock_articles_query.select.return_value.in_.return_value.execute.return_value = mock_art_res

    mock_classifications_query = MagicMock()
    mock_classifications_query.select.return_value.in_.return_value.execute.return_value = mock_cls_res

    mock_supabase = MagicMock()
    
    def mock_table(table_name):
        if table_name == "deliveries":
            return mock_deliveries_query
        elif table_name == "insights":
            return mock_insights_query
        elif table_name == "articles":
            return mock_articles_query
        elif table_name == "classifications":
            return mock_classifications_query
        return MagicMock()

    mock_supabase.table.side_effect = mock_table

    # Mock settings: disabled quiet hours
    mock_settings = {
        "high_threshold": 85,
        "digest_threshold": 60,
        "max_per_run": 5,
        "quiet_hours": {
            "enabled": False,
            "start": 22,
            "end": 6
        }
    }
    
    with patch("delivery.ntfy_delivery.create_client", return_value=mock_supabase), \
         patch("delivery.ntfy_delivery.load_notification_settings", return_value=mock_settings):
        deliver_pending_insights()
        
    # Check that exactly 3 pushes were sent to ntfy:
    # - 2 high-tier individual pushes (for scores 90 and 88)
    # - 1 bundled digest push (for scores 75 and 70)
    # - 0 pushes for low-tier (scores 50 and 40)
    assert ntfy_route.call_count == 3
    
    # Check mock deliveries insert calls (should log all 6 insights)
    # There should be 2 inserts for high tier, 2 inserts for digest tier, and 2 inserts for low tier
    insert_calls = mock_deliveries_query.insert.call_count
    assert insert_calls == 6
    
    # Verify content formatting on the pushes
    first_req = ntfy_route.calls[0].request
    assert "Headline 0" in first_req.headers.get("Title") or "Headline 1" in first_req.headers.get("Title")
    
    # Last request should be the digest bundle
    digest_req = ntfy_route.calls[2].request
    assert "Glacex.ai Digest" in digest_req.headers.get("Title")
    body = digest_req.content.decode('utf-8')
    assert "score 75" in body
    assert "score 70" in body

@respx.mock
def test_deliver_pending_insights_quiet_hours():
    # Mock ntfy.sh POST route using re.compile
    ntfy_route = respx.post(url=re.compile(r"https://ntfy.sh/.*")).respond(status_code=200, text="ok")
    
    mock_supabase = MagicMock()
    # Mock settings: enabled quiet hours
    mock_settings = {
        "high_threshold": 85,
        "digest_threshold": 60,
        "max_per_run": 10,
        "quiet_hours": {
            "enabled": True,
            "start": 22,
            "end": 6
        }
    }
    
    # Mock current time hour to be inside quiet hours (e.g., 23:00)
    mock_now = MagicMock()
    mock_now.hour = 23
    
    with patch("delivery.ntfy_delivery.create_client", return_value=mock_supabase), \
         patch("delivery.ntfy_delivery.load_notification_settings", return_value=mock_settings), \
         patch("datetime.datetime") as mock_datetime:
        mock_datetime.now.return_value = mock_now
        deliver_pending_insights()
        
    # Check that no ntfy push was triggered due to quiet hours deferral
    assert ntfy_route.call_count == 0
    # No deliveries logged
    assert mock_supabase.table("deliveries").insert.call_count == 0


# ── Feedback action-button tests ─────────────────────────────────────────────

@respx.mock
def test_send_insight_push_includes_feedback_action_buttons():
    """Individual push with article_id must include Good Signal / Noise action buttons."""
    ntfy_route = respx.post(url=re.compile(r"https://ntfy.sh/.*")).respond(
        status_code=200, text="ok"
    )

    article_id = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"

    from unittest.mock import patch, MagicMock
    mock_breaker = MagicMock()
    mock_breaker.call.side_effect = lambda fn: fn()  # pass-through

    # PersistentCircuitBreaker is imported lazily inside send_insight_push,
    # so patch it at the source module, not the ntfy_delivery module namespace.
    with patch("delivery.ntfy_delivery.NTFY_TOPIC", "test_topic"), \
         patch("agents.circuit_breaker.PersistentCircuitBreaker", return_value=mock_breaker), \
         patch.dict(os.environ, {"GITHUB_REPOSITORY": "testowner/testrepo"}):
        result = send_insight_push(
            headline="Breakthrough LLM Released",
            message_body="A new model beats all benchmarks.",
            url="https://example.com/article",
            category="research",
            priority=4,
            is_digest=False,
            article_id=article_id,
        )

    assert result is True
    assert ntfy_route.call_count == 1

    sent_request = ntfy_route.calls[0].request
    actions_header = sent_request.headers.get("Actions", "")

    # Both action buttons must be present
    assert "Good Signal" in actions_header, f"Expected 'Good Signal' in Actions header: {actions_header}"
    assert "Noise" in actions_header, f"Expected 'Noise' in Actions header: {actions_header}"

    # article_id must be embedded in the webhook body
    assert article_id in actions_header, f"Expected article_id in Actions header: {actions_header}"

    # Both ratings must appear in the payload
    assert '"rating": "good"' in actions_header or "'rating': 'good'" in actions_header or "\\\"rating\\\": \\\"good\\\"" in actions_header
    assert "noise" in actions_header


@respx.mock
def test_send_insight_push_digest_has_no_feedback_buttons():
    """Digest pushes must NOT include action buttons (they bundle multiple articles)."""
    ntfy_route = respx.post(url=re.compile(r"https://ntfy.sh/.*")).respond(
        status_code=200, text="ok"
    )

    from unittest.mock import patch, MagicMock
    mock_breaker = MagicMock()
    mock_breaker.call.side_effect = lambda fn: fn()

    with patch("delivery.ntfy_delivery.NTFY_TOPIC", "test_topic"), \
         patch("agents.circuit_breaker.PersistentCircuitBreaker", return_value=mock_breaker):
        result = send_insight_push(
            headline="Glacex.ai Digest (3 items)",
            message_body="• Item 1\n• Item 2\n• Item 3",
            url="",
            category="digest",
            priority=3,
            is_digest=True,
            article_id=None,  # no article_id for digests
        )

    assert result is True
    assert ntfy_route.call_count == 1

    sent_request = ntfy_route.calls[0].request
    # Actions header must NOT be present for digest pushes
    assert "Actions" not in sent_request.headers, \
        "Digest push should not include feedback action buttons"


@respx.mock
def test_high_tier_push_receives_article_id():
    """deliver_pending_insights must pass article_id to send_insight_push for high-tier items."""
    ntfy_route = respx.post(url=re.compile(r"https://ntfy.sh/.*")).respond(
        status_code=200, text="ok"
    )

    mock_del_res = MagicMock()
    mock_del_res.data = []

    mock_ins_res = MagicMock()
    mock_ins_res.data = [
        {
            "id": "insight-high-1",
            "headline": "Major AI Breakthrough",
            "tldr": ["A new model surpasses GPT-4."],
            "category": "research",
            "article_id": "article-uuid-0001",
        }
    ]

    mock_art_res = MagicMock()
    mock_art_res.data = [{"id": "article-uuid-0001", "url": "https://example.com/high"}]

    mock_cls_res = MagicMock()
    mock_cls_res.data = [{"article_id": "article-uuid-0001", "importance": 92}]

    mock_deliveries_query = MagicMock()
    mock_deliveries_query.select.return_value.eq.return_value.execute.return_value = mock_del_res
    mock_deliveries_query.insert.return_value.execute.return_value = MagicMock()

    mock_insights_query = MagicMock()
    mock_insights_query.select.return_value.execute.return_value = mock_ins_res

    mock_articles_query = MagicMock()
    mock_articles_query.select.return_value.in_.return_value.execute.return_value = mock_art_res

    mock_classifications_query = MagicMock()
    mock_classifications_query.select.return_value.in_.return_value.execute.return_value = mock_cls_res

    mock_supabase = MagicMock()

    def mock_table(table_name):
        if table_name == "deliveries":
            return mock_deliveries_query
        elif table_name == "insights":
            return mock_insights_query
        elif table_name == "articles":
            return mock_articles_query
        elif table_name == "classifications":
            return mock_classifications_query
        return MagicMock()

    mock_supabase.table.side_effect = mock_table

    mock_settings = {
        "high_threshold": 85,
        "digest_threshold": 60,
        "max_per_run": 10,
        "quiet_hours": {"enabled": False, "start": 22, "end": 6},
    }

    with patch("delivery.ntfy_delivery.create_client", return_value=mock_supabase), \
         patch("delivery.ntfy_delivery.load_notification_settings", return_value=mock_settings), \
         patch.dict(os.environ, {"GITHUB_REPOSITORY": "testowner/testrepo"}):
        deliver_pending_insights()

    assert ntfy_route.call_count == 1
    sent_request = ntfy_route.calls[0].request
    actions_header = sent_request.headers.get("Actions", "")

    # The article_id must flow all the way from the insight record into the push header
    assert "article-uuid-0001" in actions_header, \
        f"article_id not found in Actions header: {actions_header}"
