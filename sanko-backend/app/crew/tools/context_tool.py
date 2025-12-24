"""
Context Tool for CrewAI

Purpose: Allow agents to retrieve detailed content from specific 
document sections stored in the KnowledgeBase.
"""

from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from app.models.schemas import KnowledgeBase

class ReadSectionToolInput(BaseModel):
    """Input for the ReadSectionTool."""
    section_title: str = Field(description="The exact title of the section to read.")

class ReadSectionTool(BaseTool):
    name: str = "Read Document Section"
    description: str = "Retrieves the full text and LaTeX content of a specific section from the user's uploaded documents."
    args_schema: Type[BaseModel] = ReadSectionToolInput
    
    # We pass the knowledge_base directly to the tool instance
    kb: KnowledgeBase = Field(..., description="The KnowledgeBase to query.")

    def _run(self, section_title: str) -> str:
        """Execute the tool."""
        # Find the section by title (case-insensitive)
        for section in self.kb.sections:
            if section.title.lower() == section_title.lower():
                # Format the output for the agent
                result = f"## {section.title}\n\n{section.content}"
                if section.visuals:
                    result += "\n\n### Visual Elements in this Section:\n"
                    result += "\n".join([f"- {v}" for v in section.visuals])
                return result
        
        return f"Error: Section '{section_title}' not found. Available sections: {', '.join(self.kb.get_section_titles())}"
