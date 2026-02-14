"""
Context Tool for CrewAI

Purpose: Allow agents to retrieve EXACT, VERBATIM content from specific 
document sections stored in the KnowledgeBase. This preserves the original
text for accurate citations and references in generated slides.

IMPORTANT: This tool returns the FULL content without summarization.
"""

from typing import Type, Optional, List, Tuple
import re
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from app.models.schemas import KnowledgeBase


class ReadSectionToolInput(BaseModel):
    """Input for the ReadSectionTool."""
    section_title: str = Field(description="The exact title of the section to read.")


class ListSectionsToolInput(BaseModel):
    """Input for the ListSectionsTool (no input required)."""
    pass


class ReadSectionByIdToolInput(BaseModel):
    """Input for deterministic section lookup by id."""
    section_id: str = Field(description="Stable section_id from List/Search tools.")


class SearchSectionsToolInput(BaseModel):
    """Input for searching relevant sections."""
    query: str = Field(description="Search query for section retrieval.")
    max_results: int = Field(default=5, ge=1, le=20)


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


class ReadSectionByIdTool(BaseTool):
    """
    Retrieves EXACT, VERBATIM text by stable section_id.
    This is deterministic and avoids title collision ambiguity.
    """
    name: str = "Read Document Section By ID"
    description: str = (
        "Retrieves EXACT, VERBATIM section content by section_id. "
        "Use this when strict source traceability is required."
    )
    args_schema: Type[BaseModel] = ReadSectionByIdToolInput

    kb: KnowledgeBase = Field(..., description="The KnowledgeBase to query.")

    def _run(self, section_id: str) -> str:
        for section in self.kb.sections:
            if (section.section_id or "").strip().lower() == section_id.strip().lower():
                result = f"## {section.title}\n"
                result += f"**Section ID: {section.section_id or 'n/a'}**\n"
                if section.document_name:
                    result += f"**Document: {section.document_name}**\n"
                if section.page_range:
                    result += f"**Source: Pages {section.page_range}**\n"
                result += f"\n### Full Content (Verbatim):\n{section.content}"
                if section.visuals:
                    result += "\n\n### Visual Elements in this Section:\n"
                    result += "\n".join([f"- {v}" for v in section.visuals])
                return result

        available_ids = [s.section_id for s in self.kb.sections if s.section_id]
        return (
            f"Error: section_id '{section_id}' not found.\n"
            f"Available section_ids:\n" + "\n".join([f"- {sid}" for sid in available_ids[:100]])
        )


class SearchSectionsTool(BaseTool):
    """
    Searches sections by title/content tokens and returns ranked matches.
    """
    name: str = "Search Document Sections"
    description: str = (
        "Searches uploaded document sections and returns ranked matches with "
        "section_id, title, page range, and source document."
    )
    args_schema: Type[BaseModel] = SearchSectionsToolInput

    kb: KnowledgeBase = Field(..., description="The KnowledgeBase to query.")

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in re.split(r"[^a-zA-Z0-9]+", text.lower()) if t]

    def _score(self, query_tokens: List[str], title: str, content: str) -> Tuple[int, int]:
        title_tokens = set(self._tokenize(title))
        content_tokens = set(self._tokenize(content[:4000]))
        title_hits = sum(1 for t in query_tokens if t in title_tokens)
        content_hits = sum(1 for t in query_tokens if t in content_tokens)
        return (title_hits * 3 + content_hits, title_hits)

    def _run(self, query: str, max_results: int = 5) -> str:
        if not self.kb.sections:
            return "No sections found in the uploaded documents."

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return "Query is empty after tokenization."

        ranked = []
        for s in self.kb.sections:
            score, title_hits = self._score(query_tokens, s.title, s.content)
            if score > 0:
                ranked.append((score, title_hits, s))

        ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
        top = ranked[:max_results]

        if not top:
            return f"No matching sections found for query: '{query}'."

        lines = [f"## Section Search Results for: {query}", ""]
        for i, (score, _title_hits, s) in enumerate(top, 1):
            page_info = f"Pages {s.page_range}" if s.page_range else "Pages n/a"
            doc_info = s.document_name or "unknown document"
            sid = s.section_id or f"untagged-{i}"
            preview = s.content[:220].replace("\n", " ").strip()
            if len(s.content) > 220:
                preview += "..."
            lines.append(
                f"{i}. [{sid}] {s.title} | {page_info} | {doc_info} | score={score}\n"
                f"   {preview}"
            )

        return "\n".join(lines)


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
            section_id = section.section_id or f"sec-{i}"
            doc_info = f" | {section.document_name}" if section.document_name else ""
            result += f"{i}. **{section.title}** [{section_id}]{page_info}{visual_info}{doc_info}\n"
        
        return result
