import pytest
import os
import json
import datetime
import uuid
from unittest.mock import patch, MagicMock
from agents.delivery_agent import run_delivery
from delivery.ntfy_delivery import check_quiet_hours

def test_check_quiet_hours_cases():
    # Simple quiet hours
    assert check_quiet_hours(4, 22, 6) is True
    assert check_quiet_hours(23, 22, 6) is True
    assert check_quiet_hours(12, 22, 6) is False
    
    # Overlapping boundary
    assert check_quiet_hours(22, 22, 6) is True
    assert check_quiet_hours(6, 22, 6) is False

@patch("agents.delivery_agent.create_client")
@patch("agents.delivery_agent.deliver_pending_insights")
@patch("agents.delivery_agent.send_insight_push")
@patch("sentry_sdk.capture_message")
def test_run_delivery_health_monitoring(mock_capture_message, mock_send_insight_push, mock_deliver, mock_create_client):
    # Setup mock local state
    run_id = str(uuid.uuid4())
    start_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=10)).isoformat()
    state = {
        "run_id": run_id,
        "sources_total": 5,
        "sources_successful": 4,  # 80% source rate
        "ingested": 12,
        "embedded": 12,
        "duplicates": 2,
        "analyzed": 10,
        "total_llm_attempts": 10,
        "failed_llm_validations": 1,  # 90% success rate
        "new_signals": 3,  # 60% signal yield against expected 5
        "delivered": 0,
        "start_time": start_time
    }
    
    # Write mock state to file
    state_file = "pipeline_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)

    try:
        # Mock Supabase client
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        # Mock responses
        mock_del_res = MagicMock()
        mock_del_res.data = [{"id": "del-1"}, {"id": "del-2"}]
        
        mock_prev_health_res = MagicMock()
        mock_prev_health_res.data = [{"health_score": 0.45}]
        
        # Pre-create query mocks to maintain references for assertions
        mock_deliveries_query = MagicMock()
        mock_deliveries_query.select.return_value.gt.return_value.execute.return_value = mock_del_res
        
        mock_health_query = MagicMock()
        mock_health_query.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_prev_health_res
        mock_health_query.insert.return_value.execute.return_value = MagicMock()
        
        mock_runs_query = MagicMock()
        mock_runs_query.insert.return_value.execute.return_value = MagicMock()
        
        def mock_table(table_name):
            if table_name == "deliveries":
                return mock_deliveries_query
            elif table_name == "pipeline_health":
                return mock_health_query
            elif table_name == "pipeline_runs":
                return mock_runs_query
            return MagicMock()
            
        mock_supabase.table.side_effect = mock_table
        
        run_delivery()
        
        # Check database logs
        assert mock_runs_query.insert.call_count == 1
        runs_payload = mock_runs_query.insert.call_args[0][0]
        assert runs_payload["id"] == run_id
        assert runs_payload["ingested"] == 12
        assert runs_payload["duplicates"] == 2
        assert runs_payload["new_signals"] == 3
        
        # Check that pipeline_health insert was called with score
        assert mock_health_query.insert.call_count == 1
        health_payload = mock_health_query.insert.call_args[0][0]
        assert health_payload["run_id"] == run_id
        assert abs(health_payload["health_score"] - 0.74) < 1e-5
        assert health_payload["sources_successful"] == 4
        assert health_payload["sources_total"] == 5
        assert health_payload["llm_success_rate"] == 0.9
        
        # Check Sentry and ntfy alerts were NOT called
        assert mock_capture_message.call_count == 0
        assert mock_send_insight_push.call_count == 0
        
        # Check local state file is cleaned up
        assert not os.path.exists(state_file)
        
    finally:
        if os.path.exists(state_file):
            os.remove(state_file)

@patch("agents.delivery_agent.create_client")
@patch("agents.delivery_agent.deliver_pending_insights")
@patch("agents.delivery_agent.send_insight_push")
@patch("sentry_sdk.capture_message")
def test_run_delivery_consecutive_degradation_alert(mock_capture_message, mock_send_insight_push, mock_deliver, mock_create_client):
    # Setup mock local state with degraded stats
    run_id = str(uuid.uuid4())
    state = {
        "run_id": run_id,
        "sources_total": 5,
        "sources_successful": 2,
        "ingested": 2,
        "embedded": 2,
        "duplicates": 0,
        "analyzed": 5,
        "total_llm_attempts": 5,
        "failed_llm_validations": 3,
        "new_signals": 1,
        "delivered": 0,
        "start_time": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    
    state_file = "pipeline_state.json"
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f)

    try:
        mock_supabase = MagicMock()
        mock_create_client.return_value = mock_supabase
        
        mock_del_res = MagicMock()
        mock_del_res.data = []
        
        mock_prev_health_res = MagicMock()
        mock_prev_health_res.data = [{"health_score": 0.35}]
        
        # Pre-create query mocks
        mock_deliveries_query = MagicMock()
        mock_deliveries_query.select.return_value.gt.return_value.execute.return_value = mock_del_res
        
        mock_health_query = MagicMock()
        mock_health_query.select.return_value.order.return_value.limit.return_value.execute.return_value = mock_prev_health_res
        mock_health_query.insert.return_value.execute.return_value = MagicMock()
        
        mock_runs_query = MagicMock()
        mock_runs_query.insert.return_value.execute.return_value = MagicMock()
        
        def mock_table(table_name):
            if table_name == "deliveries":
                return mock_deliveries_query
            elif table_name == "pipeline_health":
                return mock_health_query
            elif table_name == "pipeline_runs":
                return mock_runs_query
            return MagicMock()
            
        mock_supabase.table.side_effect = mock_table
        
        run_delivery()
        
        # Check that Sentry and ntfy alerts WERE triggered
        assert mock_capture_message.call_count == 1
        assert mock_send_insight_push.call_count == 1
        
        # Verify alert payload details
        alert_args = mock_send_insight_push.call_args[1]
        assert alert_args["category"] == "health"
        assert alert_args["priority"] == 5
        assert "consecutive runs" in alert_args["message_body"]
        
    finally:
        if os.path.exists(state_file):
            os.remove(state_file)
