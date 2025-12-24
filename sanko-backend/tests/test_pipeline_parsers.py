"""
Tests for Pipeline Parsers

Tests the response parsing utilities.
"""

import pytest
from unittest.mock import MagicMock

from app.pipeline.parsers import (
    parse_enriched_content,
    skeleton_to_enriched_fallback,
)


class TestSkeletonToEnrichedFallback:
    """Tests for skeleton_to_enriched_fallback function."""
    
    def test_basic_fallback(self):
        """Test basic fallback conversion."""
        # Create mock skeleton slide
        slide = MagicMock()
        slide.order = 1
        slide.title = "Test Slide"
        slide.bullet_points = ["Point 1", "Point 2"]
        slide.content_type = "content"
        slide.equation_latex = None
        slide.speaker_notes_hint = "Speaker notes here"
        
        skeleton = MagicMock()
        skeleton.presentation_title = "Test Presentation"
        skeleton.target_audience = "Students"
        skeleton.slides = [slide]
        
        order_form = MagicMock()
        order_form.theme_id = "modern"
        order_form.citation_style = "apa"
        
        result = skeleton_to_enriched_fallback(skeleton, order_form)
        
        assert result.presentation_title == "Test Presentation"
        assert result.target_audience == "Students"
        assert result.theme_id == "modern"
        assert len(result.slides) == 1
        assert result.slides[0].title == "Test Slide"


class TestParseEnrichedContent:
    """Tests for parse_enriched_content function."""
    
    def test_valid_json_response(self):
        """Test parsing valid JSON response."""
        response = '''
        {
            "presentation_title": "AI Overview",
            "target_audience": "Engineers",
            "slides": [
                {
                    "order": 1,
                    "title": "Introduction",
                    "content_type": "overview",
                    "bullet_points": ["What is AI", "History"]
                }
            ]
        }
        '''
        
        skeleton = MagicMock()
        skeleton.presentation_title = "Fallback Title"
        skeleton.target_audience = "Fallback Audience"
        skeleton.slides = []
        
        order_form = MagicMock()
        order_form.theme_id = "modern"
        order_form.citation_style = "apa"
        
        result = parse_enriched_content(response, skeleton, order_form)
        
        assert result.presentation_title == "AI Overview"
        assert len(result.slides) == 1
        assert result.slides[0].title == "Introduction"
    
    def test_fallback_on_invalid_json(self):
        """Test fallback when JSON is invalid."""
        response = "This is not valid JSON at all"
        
        slide = MagicMock()
        slide.order = 1
        slide.title = "Fallback Slide"
        slide.bullet_points = ["Fallback point"]
        slide.content_type = "content"
        slide.equation_latex = None
        slide.speaker_notes_hint = None
        
        skeleton = MagicMock()
        skeleton.presentation_title = "Fallback Title"
        skeleton.target_audience = "Fallback Audience"
        skeleton.slides = [slide]
        
        order_form = MagicMock()
        order_form.theme_id = "modern"
        order_form.citation_style = "apa"
        
        result = parse_enriched_content(response, skeleton, order_form)
        
        # Should return fallback
        assert result.presentation_title == "Fallback Title"
    
    def test_normalize_slide_number_to_order(self):
        """Test that slide_number is normalized to order."""
        response = '''
        {
            "slides": [
                {
                    "slide_number": 5,
                    "title": "Test",
                    "content_type": "content",
                    "bullet_points": ["Test"]
                }
            ]
        }
        '''
        
        skeleton = MagicMock()
        skeleton.presentation_title = "Test"
        skeleton.target_audience = "Test"
        skeleton.slides = []
        
        order_form = MagicMock()
        order_form.theme_id = "modern"
        order_form.citation_style = "apa"
        
        result = parse_enriched_content(response, skeleton, order_form)
        
        assert result.slides[0].order == 5
    
    def test_normalize_type_to_content_type(self):
        """Test that type is normalized to content_type."""
        response = '''
        {
            "slides": [
                {
                    "order": 1,
                    "title": "Test",
                    "type": "overview",
                    "bullet_points": ["Test"]
                }
            ]
        }
        '''
        
        skeleton = MagicMock()
        skeleton.presentation_title = "Test"
        skeleton.target_audience = "Test"
        skeleton.slides = []
        
        order_form = MagicMock()
        order_form.theme_id = "modern"
        order_form.citation_style = "apa"
        
        result = parse_enriched_content(response, skeleton, order_form)
        
        assert result.slides[0].content_type == "overview"
