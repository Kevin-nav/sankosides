"""
Tests for the SynthesisTool (v8.0).

This test file verifies the SynthesisTool correctly delegates to
the GeminiExtractionService for optimized PDF extraction.
"""
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from app.crew.tools.synthesis_tool import SynthesisTool, SynthesisToolInput, SynthesisError
from app.models.schemas import KnowledgeBase, DocumentSection


def test_synthesis_tool_run():
    """Test the synthesis tool with mocked GeminiExtractionService."""
    tool = SynthesisTool()
    
    # Create a mock KnowledgeBase to return
    mock_kb = KnowledgeBase(
        summary="This is a test summary.",
        sections=[
            DocumentSection(
                title="Introduction",
                content="This is the introduction.",
                visuals=[],
                page_range="1"
            )
        ]
    )
    
    # Mock the GeminiExtractionService
    mock_service = MagicMock()
    mock_service.extract_from_pdf.return_value = mock_kb
    
    with patch('app.crew.tools.synthesis_tool.Path') as mock_path:
        mock_path.return_value.exists.return_value = True
        with patch('app.services.gemini_extraction.GeminiExtractionService', return_value=mock_service):
            result = tool._run(file_path="dummy/path.pdf")
            
            # Assertions
            assert isinstance(result, KnowledgeBase)
            assert result.summary == "This is a test summary."
            assert len(result.sections) == 1
            assert result.sections[0].title == "Introduction"


def test_synthesis_tool_input_schema():
    """Verify the input schema."""
    assert SynthesisToolInput.model_fields['file_path'].description == "The path to the PDF file to be synthesized."


def test_synthesis_tool_missing_api_key():
    """Test that SynthesisError is raised when API key is missing."""
    tool = SynthesisTool()
    
    mock_service_class = MagicMock()
    mock_service_class.side_effect = ValueError("GEMINI_API_KEY not configured")
    
    with patch('app.crew.tools.synthesis_tool.Path') as mock_path:
        mock_path.return_value.exists.return_value = True
        with patch('app.services.gemini_extraction.GeminiExtractionService', mock_service_class):
            with pytest.raises(SynthesisError) as exc_info:
                tool._run(file_path="dummy/path.pdf")
            
            assert "GEMINI_API_KEY not configured" in str(exc_info.value)


def test_synthesis_tool_file_not_found():
    """Test that SynthesisError is raised when file doesn't exist."""
    tool = SynthesisTool()
    
    with patch('app.crew.tools.synthesis_tool.Path') as mock_path:
        mock_path.return_value.exists.return_value = False
        with pytest.raises(SynthesisError) as exc_info:
            tool._run(file_path="nonexistent/path.pdf")
        
        assert "File not found" in str(exc_info.value)


def test_synthesis_tool_extraction_failure():
    """Test that SynthesisError is raised when extraction fails."""
    tool = SynthesisTool()
    
    mock_service = MagicMock()
    mock_service.extract_from_pdf.side_effect = RuntimeError("Batch job failed")
    
    with patch('app.crew.tools.synthesis_tool.Path') as mock_path:
        mock_path.return_value.exists.return_value = True
        with patch('app.services.gemini_extraction.GeminiExtractionService', return_value=mock_service):
            with pytest.raises(SynthesisError) as exc_info:
                tool._run(file_path="dummy/path.pdf")
            
            assert "Synthesis failed" in str(exc_info.value)
