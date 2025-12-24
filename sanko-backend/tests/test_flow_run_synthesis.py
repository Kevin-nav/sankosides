import pytest
from unittest.mock import patch, MagicMock
from app.crew.flows.slide_generation import SlideGenerationFlow, FlowStatus
from app.models.schemas import KnowledgeBase, DocumentSection

@pytest.mark.asyncio
async def test_run_synthesis_success():
    # Setup
    flow = SlideGenerationFlow(session_id="test-session")
    file_paths = ["file1.pdf", "file2.pdf"]
    
    # Mock data
    kb1 = KnowledgeBase(
        summary="Summary 1",
        sections=[DocumentSection(title="S1", content="C1")]
    )
    kb2 = KnowledgeBase(
        summary="Summary 2",
        sections=[DocumentSection(title="S2", content="C2")]
    )
    
    # Mock SynthesisTool._run
    # We mock it at the class level or instance level where it's used in the flow
    with patch('app.crew.flows.slide_generation.SynthesisTool') as MockTool:
        mock_tool_instance = MockTool.return_value
        mock_tool_instance._run.side_effect = [kb1, kb2]
        
        # Run
        result = await flow.run_synthesis(file_paths)
        
        # Assertions
        assert flow.state.status == FlowStatus.AWAITING_CLARIFICATION
        assert flow.state.knowledge_base is not None
        assert len(flow.state.knowledge_base.sections) == 2
        assert "Summary 1" in flow.state.knowledge_base.summary
        assert "Summary 2" in flow.state.knowledge_base.summary
        assert result == flow.state.knowledge_base
        assert mock_tool_instance._run.call_count == 2

@pytest.mark.asyncio
async def test_run_synthesis_with_error():
    flow = SlideGenerationFlow(session_id="test-session")
    file_paths = ["error.pdf"]
    
    with patch('app.crew.flows.slide_generation.SynthesisTool') as MockTool:
        mock_tool_instance = MockTool.return_value
        mock_tool_instance._run.return_value = "Error: Something went wrong"
        
        # Run
        result = await flow.run_synthesis(file_paths)
        
        # Assertions - should continue but result in empty sections if all failed
        assert len(result.sections) == 0
        assert flow.state.status == FlowStatus.AWAITING_CLARIFICATION
