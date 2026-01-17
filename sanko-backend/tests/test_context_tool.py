import pytest
from app.crew.tools.context_tool import ReadSectionTool, ReadSectionToolInput, ListSectionsTool
from app.models.schemas import KnowledgeBase, DocumentSection

def test_read_section_tool_success():
    kb = KnowledgeBase(
        summary="Test summary",
        sections=[
            DocumentSection(
                title="Introduction", 
                content="This is the intro.",
                visuals=["System diagram"],
                page_range="1-3"
            ),
            DocumentSection(title="Data", content="Data details.")
        ]
    )
    
    tool = ReadSectionTool(kb=kb)
    
    # Test case-insensitive match
    result = tool._run(section_title="introduction")
    
    assert "## Introduction" in result
    assert "This is the intro." in result
    assert "System diagram" in result
    # New: Check for page range in output
    assert "Pages 1-3" in result

def test_read_section_tool_not_found():
    kb = KnowledgeBase(summary="S", sections=[DocumentSection(title="S1", content="C1")])
    tool = ReadSectionTool(kb=kb)
    
    result = tool._run(section_title="Missing")
    
    assert "Error: Section 'Missing' not found" in result
    # New format uses bullet points
    assert "- S1" in result

def test_read_section_tool_input_schema():
    assert ReadSectionToolInput.model_fields['section_title'].description == "The exact title of the section to read."

def test_list_sections_tool():
    """Test the ListSectionsTool."""
    kb = KnowledgeBase(
        summary="Test summary",
        sections=[
            DocumentSection(title="Intro", content="...", page_range="1"),
            DocumentSection(title="Methods", content="...", visuals=["chart1"]),
        ]
    )
    
    tool = ListSectionsTool(kb=kb)
    result = tool._run()
    
    assert "**Intro**" in result
    assert "**Methods**" in result
    assert "(Pages 1)" in result
    assert "[1 visuals]" in result
