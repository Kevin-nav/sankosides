"""
Tests for Pipeline Formatters

Tests the prompt formatting utilities.
"""

import pytest
from unittest.mock import MagicMock

from app.pipeline.formatters import (
    format_skeleton_for_prompt,
    format_enriched_for_prompt,
)


class TestFormatSkeletonForPrompt:
    """Tests for format_skeleton_for_prompt function."""
    
    def test_basic_skeleton(self):
        """Test formatting a basic skeleton."""
        # Create mock skeleton
        slide = MagicMock()
        slide.order = 1
        slide.title = "Introduction"
        slide.content_type = "overview"
        slide.bullet_points = ["Point 1", "Point 2"]
        slide.needs_citation = False
        slide.needs_diagram = False
        slide.needs_equation = False
        
        skeleton = MagicMock()
        skeleton.slides = [slide]
        
        result = format_skeleton_for_prompt(skeleton)
        
        assert "Slide 1: Introduction" in result
        assert "Type: overview" in result
        assert "Point 1" in result
    
    def test_skeleton_with_citations(self):
        """Test skeleton slide needing citations."""
        slide = MagicMock()
        slide.order = 2
        slide.title = "Methodology"
        slide.content_type = "content"
        slide.bullet_points = ["Approach 1"]
        slide.needs_citation = True
        slide.citation_topic = "research methodology"
        slide.needs_diagram = False
        slide.needs_equation = False
        
        skeleton = MagicMock()
        skeleton.slides = [slide]
        
        result = format_skeleton_for_prompt(skeleton)
        
        assert "NEEDS CITATION" in result
        assert "research methodology" in result
    
    def test_skeleton_with_diagram(self):
        """Test skeleton slide needing diagram."""
        slide = MagicMock()
        slide.order = 3
        slide.title = "Architecture"
        slide.content_type = "content"
        slide.bullet_points = ["Component A"]
        slide.needs_citation = False
        slide.needs_diagram = True
        slide.diagram_description = "system architecture flowchart"
        slide.needs_equation = False
        
        skeleton = MagicMock()
        skeleton.slides = [slide]
        
        result = format_skeleton_for_prompt(skeleton)
        
        assert "NEEDS DIAGRAM" in result
        assert "system architecture flowchart" in result


class TestFormatEnrichedForPrompt:
    """Tests for format_enriched_for_prompt function."""
    
    def test_basic_enriched(self):
        """Test formatting basic enriched content."""
        slide = MagicMock()
        slide.order = 1
        slide.title = "Overview"
        slide.content_type = "overview"
        slide.bullet_points = ["Key point 1", "Key point 2"]
        slide.equation_latex = None
        slide.image_url = None
        slide.citations = []
        
        enriched = MagicMock()
        enriched.slides = [slide]
        
        result = format_enriched_for_prompt(enriched)
        
        assert "Slide 1: Overview" in result
        assert "Type: overview" in result
    
    def test_enriched_with_equation(self):
        """Test enriched content with equation."""
        slide = MagicMock()
        slide.order = 2
        slide.title = "Formula"
        slide.content_type = "content"
        slide.bullet_points = ["Point"]
        slide.equation_latex = "E = mc^2"
        slide.image_url = None
        slide.citations = []
        
        enriched = MagicMock()
        enriched.slides = [slide]
        
        result = format_enriched_for_prompt(enriched)
        
        assert "EQUATION SVG: [embedded]" in result
    
    def test_enriched_with_citations(self):
        """Test enriched content with citations."""
        slide = MagicMock()
        slide.order = 3
        slide.title = "Evidence"
        slide.content_type = "content"
        slide.bullet_points = ["Finding"]
        slide.equation_latex = None
        slide.image_url = None
        slide.citations = [{"author": "Test"}]  # Non-empty list
        
        enriched = MagicMock()
        enriched.slides = [slide]
        
        result = format_enriched_for_prompt(enriched)
        
        assert "CITATIONS: 1 sources" in result
