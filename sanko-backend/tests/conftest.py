"""
Test fixtures and configuration for SankoSlides backend tests.
"""

import sys
from unittest.mock import MagicMock

# Mock external dependencies before any other imports
# This allows tests to run without the full installation

# Mock Google GenAI (only the genai module, not google namespace since crewai needs it)
# Note: We don't mock crewai or crewai.tools since they work correctly with the installed package

# Mock litellm (used by crewai internally, may not be needed for all tests)
sys.modules['litellm'] = MagicMock()

import pytest
import asyncio
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock




# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_gemini_response() -> Dict[str, Any]:
    """Standard mock response from Gemini API."""
    return {
        "response": "Mock response content",
        "thinking": "Mock thinking process",
        "interaction_id": "mock-interaction-123",
        "tokens": {
            "input": 100,
            "output": 50,
            "thinking": 25,
        }
    }


@pytest.fixture
def mock_gemini_client(mock_gemini_response):
    """Mock GeminiInteractionsClient for testing without API calls."""
    client = AsyncMock()
    client.generate_with_thinking = AsyncMock(return_value=mock_gemini_response)
    client.generate_with_thinking_stream = AsyncMock()
    client.create_interaction = AsyncMock(return_value=mock_gemini_response)
    return client


@pytest.fixture
def sample_order_form() -> Dict[str, Any]:
    """Sample OrderForm data for testing."""
    return {
        "topic": "Machine Learning Fundamentals",
        "slide_count": 10,
        "audience": "Graduate students",
        "citation_style": "apa",
        "theme_id": "modern",
        "include_equations": True,
        "include_diagrams": True,
    }


@pytest.fixture
def sample_skeleton() -> Dict[str, Any]:
    """Sample Skeleton data for testing."""
    return {
        "presentation_title": "Introduction to Machine Learning",
        "target_audience": "Graduate students",
        "slides": [
            {
                "order": 1,
                "title": "What is Machine Learning?",
                "content_type": "overview",
                "bullet_points": [
                    "Definition of ML",
                    "Types of learning",
                    "Key applications",
                ],
                "needs_citation": False,
                "needs_diagram": False,
            },
            {
                "order": 2,
                "title": "Supervised Learning",
                "content_type": "content",
                "bullet_points": [
                    "Classification vs Regression",
                    "Training and testing",
                ],
                "needs_citation": True,
                "citation_topic": "supervised learning definition",
                "needs_diagram": True,
                "diagram_description": "flowchart of supervised learning process",
            },
        ],
    }


@pytest.fixture
def sample_enriched_content() -> Dict[str, Any]:
    """Sample EnrichedContent data for testing."""
    return {
        "presentation_title": "Introduction to Machine Learning",
        "target_audience": "Graduate students",
        "theme_id": "modern",
        "citation_style": "apa",
        "slides": [
            {
                "order": 1,
                "title": "What is Machine Learning?",
                "content_type": "overview",
                "bullet_points": [
                    "Definition of ML",
                    "Types of learning",
                    "Key applications",
                ],
                "citations": [],
            },
            {
                "order": 2,
                "title": "Supervised Learning",
                "content_type": "content",
                "bullet_points": [
                    "Classification vs Regression",
                    "Training and testing",
                ],
                "citations": [
                    {
                        "authors": ["Mitchell, T."],
                        "year": 1997,
                        "title": "Machine Learning",
                        "source": "McGraw-Hill",
                    }
                ],
                "diagram_mermaid": "flowchart TD\n    A[Input] --> B[Model]\n    B --> C[Output]",
            },
        ],
    }


# ============================================================================
# Async Test Helpers
# ============================================================================

@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
