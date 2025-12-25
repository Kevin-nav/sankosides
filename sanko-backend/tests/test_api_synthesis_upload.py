import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock
from app.main import app
from app.crew.flows.slide_generation import FlowStatus

client = TestClient(app)

@pytest.mark.asyncio
@patch("app.api.routers.generation.SlideGenerationFlow")
@patch("app.api.routers.generation.create_session")
async def test_start_session_with_files(mock_create_session, MockFlowClass):
    # Setup mock state
    mock_state = MagicMock()
    mock_state.session_id = "test-session-123"
    mock_state.status = FlowStatus.AWAITING_CLARIFICATION
    
    mock_create_session.return_value = mock_state
    
    # Setup mock flow instance
    mock_flow_instance = MockFlowClass.return_value
    mock_flow_instance.run_synthesis = AsyncMock()
    
    # Simulate file upload
    files = [
        ("files", ("test.pdf", b"fake pdf content", "application/pdf"))
    ]
    
    # Run request
    response = client.post("/api/generation/start", files=files)
    
    # Assertions
    assert response.status_code == 200
    assert response.json()["session_id"] == "test-session-123"
    mock_flow_instance.run_synthesis.assert_called_once()
    
    # Cleanup: remove created directory if needed (optional for mock tests)
    import shutil
    from pathlib import Path
    shutil.rmtree(Path("generated_assets/uploads") / "test-session-123", ignore_errors=True)