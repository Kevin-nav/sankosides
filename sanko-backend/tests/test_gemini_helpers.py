"""
Tests for Gemini Service Helpers

Tests token extraction and part building utilities.
"""

import pytest
from unittest.mock import MagicMock

from app.services.gemini.helpers import (
    extract_token_usage,
    extract_thinking_from_response,
    extract_text_from_response,
)


class TestExtractTokenUsage:
    """Tests for extract_token_usage function."""
    
    def test_interactions_api_usage(self):
        """Test token extraction from Interactions API response."""
        response = MagicMock()
        response.usage = MagicMock()
        response.usage.total_input_tokens = 100
        response.usage.total_output_tokens = 50
        response.usage.total_thought_tokens = 25
        response.usage.cached_tokens = 10
        
        result = extract_token_usage(response)
        
        assert result["input_tokens"] == 100
        assert result["output_tokens"] == 50
        assert result["thinking_tokens"] == 25
        assert result["cached_tokens"] == 10
        assert result["total_tokens"] == 175
    
    def test_generate_content_usage_metadata(self):
        """Test token extraction from generate_content response."""
        response = MagicMock()
        response.usage = None
        response.usage_metadata = MagicMock()
        response.usage_metadata.prompt_token_count = 80
        response.usage_metadata.candidates_token_count = 40
        response.usage_metadata.thoughts_token_count = 20
        response.usage_metadata.cached_content_token_count = 5
        
        result = extract_token_usage(response)
        
        assert result["input_tokens"] == 80
        assert result["output_tokens"] == 40
        assert result["thinking_tokens"] == 20
        assert result["cached_tokens"] == 5
    
    def test_empty_response(self):
        """Test token extraction from response with no usage data."""
        response = MagicMock()
        response.usage = None
        response.usage_metadata = None
        response.metadata = None
        
        result = extract_token_usage(response)
        
        assert result["input_tokens"] == 0
        assert result["output_tokens"] == 0
        assert result["total_tokens"] == 0


class TestExtractThinking:
    """Tests for thinking extraction."""
    
    def test_extract_thinking_with_thought_parts(self):
        """Test extracting thinking from response with thought parts."""
        part = MagicMock()
        part.thought = "This is my reasoning process"
        part.text = None
        
        content = MagicMock()
        content.parts = [part]
        
        candidate = MagicMock()
        candidate.content = content
        
        response = MagicMock()
        response.candidates = [candidate]
        
        result = extract_thinking_from_response(response)
        
        assert result == "This is my reasoning process"
    
    def test_extract_thinking_empty(self):
        """Test extracting thinking when no thought parts exist."""
        response = MagicMock()
        response.candidates = []
        
        result = extract_thinking_from_response(response)
        
        assert result == ""


class TestExtractText:
    """Tests for text extraction."""
    
    def test_extract_text_from_response(self):
        """Test extracting text from response."""
        response = MagicMock()
        response.text = "This is the response content"
        
        result = extract_text_from_response(response)
        
        assert result == "This is the response content"
    
    def test_extract_text_missing(self):
        """Test extracting text when not present."""
        response = MagicMock(spec=[])  # No text attribute
        
        result = extract_text_from_response(response)
        
        assert result == ""


class TestStreamingTokenExtraction:
    """Tests for streaming token extraction behavior."""
    
    def test_record_output_accepts_token_counts(self):
        """Verify record_output accepts token parameters for streaming."""
        from app.services.metrics import AgentMetricsTracker
        
        tracker = AgentMetricsTracker()
        metric = tracker.start("test_agent", model="gemini-3-flash-preview")
        
        tracker.record_output(
            metric,
            raw_output="test output",
            raw_thinking="test thinking",
            input_tokens=100,
            output_tokens=50,
            thinking_tokens=200,
            cached_tokens=10,
        )
        
        assert metric.tokens.input_tokens == 100
        assert metric.tokens.output_tokens == 50
        assert metric.tokens.thinking_tokens == 200
        assert metric.tokens.cached_tokens == 10
    
    def test_record_output_without_tokens(self):
        """Verify record_output works without token counts (backward compatible)."""
        from app.services.metrics import AgentMetricsTracker
        
        tracker = AgentMetricsTracker()
        metric = tracker.start("test_agent", model="gemini-3-flash-preview")
        
        tracker.record_output(
            metric,
            raw_output="test output",
            raw_thinking="test thinking",
        )
        
        # Tokens should remain at default (0)
        assert metric.tokens.input_tokens == 0
        assert metric.raw_output == "test output"
        assert metric.raw_thinking == "test thinking"
    
    def test_cost_calculation_with_thinking_tokens(self):
        """Verify cost calculation includes thinking tokens."""
        from app.services.metrics import AgentMetric, TokenUsage
        
        metric = AgentMetric(
            agent_name="test",
            model="gemini-3-flash-preview",
            tokens=TokenUsage(
                input_tokens=1_000_000,  # 1M input
                output_tokens=500_000,   # 500K output
                thinking_tokens=1_000_000,  # 1M thinking
            )
        )
        
        cost = metric.calculate_cost()
        
        # Flash pricing: $0.50/1M input, $3.00/1M output, $0.50/1M thinking
        expected_cost = (1.0 * 0.50) + (0.5 * 3.00) + (1.0 * 0.50)
        assert abs(cost - expected_cost) < 0.01

