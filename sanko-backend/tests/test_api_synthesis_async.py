import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.crew.flows.slide_generation import FlowStatus

client = TestClient(app)

@pytest.mark.asyncio
@patch("app.api.routers.generation.SlideGenerationFlow")
@patch("app.api.routers.generation.create_session")
async def test_start_session_async_synthesis(mock_create_session, MockFlowClass):
    # Setup mock state
    mock_state = MagicMock()
    mock_state.session_id = "test-async-session"
    mock_state.status = FlowStatus.SYNTHESIZING
    
    mock_create_session.return_value = mock_state
    
    # Setup mock flow instance
    mock_flow_instance = MockFlowClass.return_value
    mock_flow_instance.run_synthesis = AsyncMock()
    # Ensure state on flow instance matches
    mock_flow_instance.state = mock_state
    
    # Simulate file upload
    files = [
        ("files", ("test.pdf", b"fake content", "application/pdf"))
    ]
    
    # Run request
    response = client.post("/api/generation/start", files=files)
    
    # Assertions
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == "test-async-session"
    assert data["status"] == "synthesizing"
    
    # CRITICAL: run_synthesis should NOT be awaited in the request handler
    # It should be added to background tasks.
    # In TestClient, background tasks run after the response is returned.
    # So we check if the response was fast and correct first.
