"""
Tests for the SynthesisTool.

This test file uses a different approach - instead of trying to mock the module's 
imports before they happen, we call the tool._run method and mock the specific 
objects it uses at runtime.
"""
import pytest
from unittest.mock import patch, MagicMock
from app.crew.tools.synthesis_tool import SynthesisTool, SynthesisToolInput
from app.models.schemas import KnowledgeBase


def test_synthesis_tool_run():
    """Test the synthesis tool with mocked dependencies."""
    # Create the tool first
    tool = SynthesisTool()
    
    # Mock the settings
    mock_settings = MagicMock()
    mock_settings.gemini_api_key = "fake-api-key"
    
    # Mock the Gemini API client
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = """{
        "summary": "This is a test summary.",
        "sections": [
            {
                "title": "Introduction",
                "content": "This is the introduction.",
                "visuals": [],
                "page_range": "1"
            }
        ]
    }"""
    mock_client.models.generate_content.return_value = mock_response
    
    # Patch at the module level where the objects are USED
    with patch('app.crew.tools.synthesis_tool.settings', mock_settings):
        with patch('app.crew.tools.synthesis_tool.genai.Client', return_value=mock_client):
            with patch('builtins.open', new_callable=MagicMock) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = b"fake pdf data"
                
                # Run the tool
                result = tool._run(file_path="dummy/path.pdf")
                
                # Assertions
                assert isinstance(result, KnowledgeBase), f"Expected KnowledgeBase, got {type(result)}: {result}"
                assert result.summary == "This is a test summary."
                assert len(result.sections) == 1
                assert result.sections[0].title == "Introduction"


def test_synthesis_tool_input_schema():
    """Verify the input schema."""
    assert SynthesisToolInput.model_fields['file_path'].description == "The path to the PDF file to be synthesized."
