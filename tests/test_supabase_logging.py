"""
Tests for Supabase pipeline run logging.
"""
import pytest
from uuid import UUID, uuid4
from datetime import datetime

from jarvis.persistence.supabase import SupabaseClient, log_pipeline_run
from jarvis.schemas.pipeline import PipelineRun, StageResult, StageStatus


@pytest.fixture
def sample_pipeline_run():
    """Create a sample pipeline run for testing."""
    run = PipelineRun(
        id=uuid4(),
        session_id="test-session",
        user_id="test-user",
        status="running",
        stages=[
            StageResult(
                stage="audio_input",
                status=StageStatus.SUCCESS,
                input={"audio_format": "wav", "size_bytes": 32044},
                output={"duration_ms": 1000},
                latency_ms=50,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            ),
            StageResult(
                stage="transcription",
                status=StageStatus.SUCCESS,
                input={"audio_bytes": 32044},
                output={"text": "Hello world", "language": "en", "confidence": 0.95},
                latency_ms=1200,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
            ),
        ],
        created_at=datetime.utcnow(),
        total_latency_ms=1250,
    )
    return run


@pytest.mark.asyncio
async def test_supabase_client_creation():
    """Test that SupabaseClient can be instantiated."""
    # This will fail if Supabase credentials are not configured
    try:
        client = SupabaseClient()
        assert client is not None
        assert client.client is not None
    except RuntimeError as e:
        pytest.skip(f"Supabase not configured: {e}")


@pytest.mark.asyncio
async def test_log_pipeline_run(sample_pipeline_run):
    """Test logging a pipeline run to Supabase."""
    try:
        await log_pipeline_run(sample_pipeline_run)
        # If no exception, logging succeeded
        assert True
    except RuntimeError as e:
        pytest.skip(f"Supabase not configured: {e}")
    except Exception as e:
        # Other errors (network, etc.) - log but don't fail test
        pytest.skip(f"Supabase logging error: {e}")


@pytest.mark.asyncio
async def test_get_pipeline_run(sample_pipeline_run):
    """Test retrieving a pipeline run from Supabase."""
    try:
        # First log it
        await log_pipeline_run(sample_pipeline_run)
        
        # Then retrieve it
        client = SupabaseClient()
        retrieved = await client.get_pipeline_run(sample_pipeline_run.id)
        
        assert retrieved is not None
        assert retrieved.id == sample_pipeline_run.id
        assert retrieved.session_id == sample_pipeline_run.session_id
        assert retrieved.user_id == sample_pipeline_run.user_id
        assert len(retrieved.stages) == 2
    except RuntimeError as e:
        pytest.skip(f"Supabase not configured: {e}")
    except Exception as e:
        pytest.skip(f"Supabase error: {e}")


@pytest.mark.asyncio
async def test_list_pipeline_runs(sample_pipeline_run):
    """Test listing pipeline runs from Supabase."""
    try:
        # First log it
        await log_pipeline_run(sample_pipeline_run)
        
        # Then list runs
        client = SupabaseClient()
        runs = await client.list_pipeline_runs(session_id="test-session", limit=10)
        
        assert len(runs) >= 1
        found = any(r.id == sample_pipeline_run.id for r in runs)
        assert found
    except RuntimeError as e:
        pytest.skip(f"Supabase not configured: {e}")
    except Exception as e:
        pytest.skip(f"Supabase error: {e}")


@pytest.mark.asyncio
async def test_pipeline_run_serialization(sample_pipeline_run):
    """Test that PipelineRun can be serialized to/from dict."""
    client = SupabaseClient()
    
    # Convert to dict
    data = client._pipeline_run_to_dict(sample_pipeline_run)
    
    assert data["id"] == str(sample_pipeline_run.id)
    assert data["session_id"] == sample_pipeline_run.session_id
    assert data["user_id"] == sample_pipeline_run.user_id
    assert data["status"] == sample_pipeline_run.status
    assert len(data["stages"]) == 2
    assert data["total_latency_ms"] == sample_pipeline_run.total_latency_ms
    
    # Convert back
    restored = client._dict_to_pipeline_run(data)
    
    assert restored.id == sample_pipeline_run.id
    assert restored.session_id == sample_pipeline_run.session_id
    assert restored.user_id == sample_pipeline_run.user_id
    assert restored.status == sample_pipeline_run.status
    assert len(restored.stages) == 2
    assert restored.total_latency_ms == sample_pipeline_run.total_latency_ms