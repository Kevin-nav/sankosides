"""
Tests for CrewAI Tool Wrappers

Tests that custom tools properly inherit from CrewAI BaseTool
and have correct structure for agent function calling.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


class TestCrewAIToolImports:
    """Tests that CrewAI tools can be imported."""
    
    def test_can_import_tools(self):
        """Verify all tool wrappers can be imported."""
        from app.tools.crewai_tools import (
            VisionVerificationTool,
            ImageGenerationTool,
            ImageSearchCrewTool,
            AcademicSearchCrewTool,
            create_crewai_tools,
        )
        assert VisionVerificationTool is not None
        assert ImageGenerationTool is not None
        assert ImageSearchCrewTool is not None
        assert AcademicSearchCrewTool is not None


class TestImageGenerationTool:
    """Tests for ImageGenerationTool CrewAI wrapper."""
    
    def test_inherits_from_base_tool(self):
        """Verify tool properly inherits from CrewAI BaseTool."""
        from crewai.tools import BaseTool
        from app.tools.crewai_tools import ImageGenerationTool
        
        tool = ImageGenerationTool()
        assert isinstance(tool, BaseTool)
    
    def test_has_required_attributes(self):
        """Verify tool has name and description."""
        from app.tools.crewai_tools import ImageGenerationTool
        
        tool = ImageGenerationTool()
        assert tool.name == "generate_image"
        assert "generate" in tool.description.lower()
        assert "diagram" in tool.description.lower()
    
    def test_description_guides_agent_usage(self):
        """Verify description tells agent when to use this tool."""
        from app.tools.crewai_tools import ImageGenerationTool
        
        tool = ImageGenerationTool()
        # Should mention creating/generating visuals
        assert "diagram" in tool.description.lower() or "create" in tool.description.lower()
        # Should contrast with search
        assert "not for" in tool.description.lower() or "photo" in tool.description.lower()


class TestImageSearchTool:
    """Tests for ImageSearchCrewTool."""
    
    def test_inherits_from_base_tool(self):
        """Verify tool properly inherits from CrewAI BaseTool."""
        from crewai.tools import BaseTool
        from app.tools.crewai_tools import ImageSearchCrewTool
        
        tool = ImageSearchCrewTool()
        assert isinstance(tool, BaseTool)
    
    def test_has_required_attributes(self):
        """Verify tool has name and description."""
        from app.tools.crewai_tools import ImageSearchCrewTool
        
        tool = ImageSearchCrewTool()
        assert tool.name == "search_images"
        assert "search" in tool.description.lower()
    
    def test_description_guides_agent_usage(self):
        """Verify description tells agent when to use this tool."""
        from app.tools.crewai_tools import ImageSearchCrewTool
        
        tool = ImageSearchCrewTool()
        # Should mention finding existing photos
        assert "photo" in tool.description.lower() or "existing" in tool.description.lower()


class TestVisionVerificationTool:
    """Tests for VisionVerificationTool."""
    
    def test_inherits_from_base_tool(self):
        """Verify tool properly inherits from CrewAI BaseTool."""
        from crewai.tools import BaseTool
        from app.tools.crewai_tools import VisionVerificationTool
        
        tool = VisionVerificationTool()
        assert isinstance(tool, BaseTool)
    
    def test_has_required_attributes(self):
        """Verify tool has name and description."""
        from app.tools.crewai_tools import VisionVerificationTool
        
        tool = VisionVerificationTool()
        assert tool.name == "verify_image"
        assert "verify" in tool.description.lower() or "match" in tool.description.lower()


class TestAcademicSearchTool:
    """Tests for AcademicSearchCrewTool."""
    
    def test_inherits_from_base_tool(self):
        """Verify tool properly inherits from CrewAI BaseTool."""
        from crewai.tools import BaseTool
        from app.tools.crewai_tools import AcademicSearchCrewTool
        
        tool = AcademicSearchCrewTool()
        assert isinstance(tool, BaseTool)
    
    def test_has_required_attributes(self):
        """Verify tool has name and description."""
        from app.tools.crewai_tools import AcademicSearchCrewTool
        
        tool = AcademicSearchCrewTool()
        assert tool.name == "search_citations"
        assert "academic" in tool.description.lower() or "citation" in tool.description.lower()


class TestCreateCrewAITools:
    """Tests for the factory function."""
    
    def test_creates_all_tools(self):
        """Verify factory creates all 4 tools."""
        from app.tools.crewai_tools import create_crewai_tools
        
        # Mock the underlying tools
        vision = MagicMock()
        image_gen = MagicMock()
        image_search = MagicMock()
        academic = MagicMock()
        
        tools = create_crewai_tools(vision, image_gen, image_search, academic)
        
        assert len(tools) == 4
        
        # Verify types
        tool_names = [t.name for t in tools]
        assert "verify_image" in tool_names
        assert "generate_image" in tool_names
        assert "search_images" in tool_names
        assert "search_citations" in tool_names
