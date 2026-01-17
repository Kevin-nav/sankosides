"""
Context Tool for CrewAI

Purpose: Allow agents to retrieve EXACT, VERBATIM content from specific 
document sections stored in the KnowledgeBase. This preserves the original
text for accurate citations and references in generated slides.

IMPORTANT: This tool returns the FULL content without summarization.
"""

from typing import Type, Optional, List
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from app.models.schemas import KnowledgeBase


class ReadSectionToolInput(BaseModel):
    """Input for the ReadSectionTool."""
    section_title: str = Field(description="The exact title of the section to read.")


class ListSectionsToolInput(BaseModel):
    """Input for the ListSectionsTool (no input required)."""
    pass


class ReadSectionTool(BaseTool):
    """
    Retrieves the EXACT, VERBATIM text and LaTeX content of a specific section.
    
    Returns full content including:
    - Original text (not summarized)
    - LaTeX equations as-is
    - Visual element descriptions
    - Page range for citation purposes
    """
    name: str = "Read Document Section"
    description: str = (
        "Retrieves the EXACT, VERBATIM text and LaTeX content of a specific section "
        "from the user's uploaded documents. Use this to get full content for a topic. "
        "The output includes page range information for proper citations."
    )
    args_schema: Type[BaseModel] = ReadSectionToolInput
    
    # We pass the knowledge_base directly to the tool instance
    kb: KnowledgeBase = Field(..., description="The KnowledgeBase to query.")

    def _run(self, section_title: str) -> str:
        """Execute the tool - returns EXACT content, not summarized."""
        # Find the section by title (case-insensitive)
        for section in self.kb.sections:
            if section.title.lower() == section_title.lower():
                # Build comprehensive output with citation metadata
                result = f"## {section.title}\n"
                
                # Add page range for citation purposes
                if section.page_range:
                    result += f"**Source: Pages {section.page_range}**\n"
                
                result += f"\n### Full Content (Verbatim):\n{section.content}"
                
                # Include visual elements
                if section.visuals:
                    result += "\n\n### Visual Elements in this Section:\n"
                    result += "\n".join([f"- {v}" for v in section.visuals])
                
                return result
        
        # Provide helpful error with available options
        available = self.kb.get_section_titles()
        return (
            f"Error: Section '{section_title}' not found.\n"
            f"Available sections:\n" + "\n".join([f"- {t}" for t in available])
        )


class ListSectionsTool(BaseTool):
    """
    Lists all available sections in the knowledge base.
    Use this first to see what sections are available before reading specific ones.
    """
    name: str = "List Document Sections"
    description: str = (
        "Lists all available section titles from the user's uploaded documents. "
        "Use this to discover what topics/sections are available before reading them."
    )
    args_schema: Type[BaseModel] = ListSectionsToolInput
    
    kb: KnowledgeBase = Field(..., description="The KnowledgeBase to query.")

    def _run(self) -> str:
        """List all section titles with brief metadata."""
        if not self.kb.sections:
            return "No sections found in the uploaded documents."
        
        result = "## Available Document Sections\n\n"
        for i, section in enumerate(self.kb.sections, 1):
            page_info = f" (Pages {section.page_range})" if section.page_range else ""
            visual_count = len(section.visuals) if section.visuals else 0
            visual_info = f" [{visual_count} visuals]" if visual_count > 0 else ""
            result += f"{i}. **{section.title}**{page_info}{visual_info}\n"
        
        return result
