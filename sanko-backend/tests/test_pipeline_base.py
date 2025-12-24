"""
Tests for Pipeline Base Models

Tests the SlideResult and PipelineResult models.
"""

import pytest
from app.pipeline.base import SlideResult, PipelineResult


class TestSlideResult:
    """Tests for SlideResult model."""
    
    def test_create_slide_result(self):
        """Test creating a basic SlideResult."""
        result = SlideResult(
            order=1,
            html_content="<html>...</html>",
            visual_score=0.95,
        )
        
        assert result.order == 1
        assert result.visual_score == 0.95
        assert result.iterations == 1
        assert result.visual_issues == []
    
    def test_slide_result_with_issues(self):
        """Test SlideResult with visual issues."""
        result = SlideResult(
            order=2,
            html_content="<html>...</html>",
            visual_score=0.75,
            visual_issues=["Text overflow", "Low contrast"],
            iterations=3,
        )
        
        assert len(result.visual_issues) == 2
        assert result.iterations == 3


class TestPipelineResult:
    """Tests for PipelineResult model."""
    
    def test_create_empty_result(self):
        """Test creating an empty pipeline result."""
        result = PipelineResult(success=False)
        
        assert result.success is False
        assert result.order_form is None
        assert result.slides == []
        assert result.average_visual_score == 0.0
    
    def test_create_success_result(self):
        """Test creating a successful pipeline result."""
        result = PipelineResult(
            success=True,
            average_visual_score=0.92,
            total_citations=5,
            total_qa_iterations=10,
        )
        
        assert result.success is True
        assert result.average_visual_score == 0.92
        assert result.total_citations == 5
    
    def test_result_with_error(self):
        """Test pipeline result with error."""
        result = PipelineResult(
            success=False,
            error="API connection failed",
            stage_failed="planner",
        )
        
        assert result.error == "API connection failed"
        assert result.stage_failed == "planner"
