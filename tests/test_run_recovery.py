import pytest
import uuid
import datetime
from unittest.mock import patch, MagicMock, AsyncMock
from agents.observability import (
    resolve_active_run_id,
    start_phase_checkpoint,
    complete_phase_checkpoint,
    is_phase_completed
)
from agents.ingestion_agent import main_ingestion
from agents.nlp_agent import run_nlp
from agents.dedup_agent import run_dedup

def get_mock_checkpoint(run_id, phase, completed=False):
    return {
        "run_id": str(run_id),
        "phase": phase,
        "phase_started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "phase_completed_at": datetime.datetime.now(datetime.timezone.utc).isoformat() if completed else None,
        "docs_processed": 5
    }

@patch("agents.observability.get_supabase_client")
@patch("agents.observability.load_pipeline_state")
def test_resolve_active_run_id_new(mock_load, mock_get_supabase):
    # Mock no local state and no incomplete runs in database
    mock_load.return_value = {}
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    mock_get_supabase.return_value = mock_supabase
    
    run_id = resolve_active_run_id()
    assert run_id is not None
    # Verifies it generates a valid UUID run ID
    assert uuid.UUID(run_id)

@patch("agents.observability.get_supabase_client")
@patch("agents.observability.load_pipeline_state")
def test_resolve_active_run_id_resume(mock_load, mock_get_supabase):
    # Mock no local state, but has an incomplete run in DB
    mock_load.return_value = {}
    mock_run_id = str(uuid.uuid4())
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.is_.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[{"run_id": mock_run_id}])
    mock_get_supabase.return_value = mock_supabase
    
    run_id = resolve_active_run_id()
    assert run_id == mock_run_id

@patch("agents.observability.get_supabase_client")
def test_checkpoint_lifecycle(mock_get_supabase):
    mock_supabase = MagicMock()
    mock_get_supabase.return_value = mock_supabase
    
    run_id = str(uuid.uuid4())
    
    # 1. Start checkpoint
    start_phase_checkpoint(run_id, "ingest")
    mock_supabase.table.return_value.upsert.assert_called_once()
    
    # 2. Complete checkpoint
    complete_phase_checkpoint(run_id, "ingest", 12)
    mock_supabase.table.return_value.update.assert_called_once()
    mock_supabase.table.return_value.update.return_value.eq.return_value.eq.return_value.execute.assert_called_once()

@patch("agents.observability.get_supabase_client")
def test_is_phase_completed(mock_get_supabase):
    mock_supabase = MagicMock()
    mock_get_supabase.return_value = mock_supabase
    
    run_id = str(uuid.uuid4())
    
    # Completed phase
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"phase_completed_at": "2026-06-01T23:00:00Z"}])
    assert is_phase_completed(run_id, "ingest") is True
    
    # Incomplete phase
    mock_supabase.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"phase_completed_at": None}])
    assert is_phase_completed(run_id, "ingest") is False

@pytest.mark.asyncio
@patch("agents.ingestion_agent.is_phase_completed", return_value=True)
@patch("agents.ingestion_agent.supabase")
async def test_agent_skips_when_phase_completed(mock_supabase, mock_is_completed):
    # Ingestion should check and skip since is_phase_completed is mocked to return True
    await main_ingestion()
    # Check that it did not fetch active sources
    mock_supabase.table.assert_not_called()
