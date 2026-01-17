"""
RenderService CrewAI Tool

Wraps the RenderService client as a CrewAI-compatible tool.
Allows agents to render LaTeX equations, Mermaid diagrams, and format citations.

Uses RenderWorker for thread-safe, connection-pooled HTTP calls.
"""

from typing import Optional, List, Dict, Any
from crewai.tools import BaseTool
from pydantic import Field

from app.core.logging import get_logger

logger = get_logger(__name__)


class RenderServiceTool(BaseTool):
    """
    CrewAI-compatible tool for rendering STEM content.
    
    Provides access to the Node.js rendering microservice for:
    - LaTeX → SVG (math equations)
    - Mermaid → SVG (diagrams, flowcharts)
    - Citation formatting (APA, IEEE, Harvard, Chicago)
    
    Uses RenderWorker for thread-safe connection pooling.
    """
    name: str = "render_service"
    description: str = """Use this tool to render STEM content to SVG or format citations.

Available actions:
1. render_latex: Convert LaTeX math to SVG image
   Input: {"action": "latex", "content": "E = mc^2"}
   
2. render_mermaid: Convert Mermaid diagram code to SVG
   Input: {"action": "mermaid", "content": "graph TD\\n    A-->B"}
   
3. format_citation: Format citation in specified style
   Input: {"action": "citation", "citation": {...}, "style": "apa"}

Returns SVG strings for equations/diagrams, formatted text for citations.
"""
    
    def _get_worker(self):
        """Get the singleton RenderWorker instance."""
        from app.services.render_worker import get_render_worker
        return get_render_worker()
    
    def _run(
        self,
        action: str,
        content: Optional[str] = None,
        citation: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        style: str = "apa",
    ) -> str:
        """
        Execute a render action using the connection-pooled worker.
        
        Args:
            action: "latex", "mermaid", or "citation"
            content: LaTeX or Mermaid code (for latex/mermaid actions)
            citation: Single citation dict (for citation action)
            citations: List of citations (for batch citation formatting)
            style: Citation style (apa, ieee, harvard, chicago)
            
        Returns:
            Rendered result as string (SVG for equations/diagrams, formatted text for citations)
        """
        worker = self._get_worker()
        
        try:
            if action == "latex":
                if not content:
                    return "Error: 'content' is required for latex rendering"
                result = worker.render_latex_sync(content)
                if result.get("success", True) and "svg" in result:
                    return result["svg"]
                return f"Error rendering LaTeX: {result.get('error', 'Unknown error')}"
            
            elif action == "mermaid":
                if not content:
                    return "Error: 'content' is required for mermaid rendering"
                result = worker.render_mermaid_sync(content)
                if result.get("success", True) and "svg" in result:
                    return result["svg"]
                return f"Error rendering Mermaid: {result.get('error', 'Unknown error')}"
            
            elif action == "citation":
                if citations:
                    cit_list = citations
                elif citation:
                    cit_list = [citation]
                else:
                    return "Error: 'citation' or 'citations' is required"
                
                result = worker.format_citation_sync(cit_list, style)
                
                # Handle different response formats
                if result.get("success", True) and "citations" in result:
                    formatted_list = []
                    for c in result["citations"]:
                        if isinstance(c, str):
                            formatted_list.append(c)
                        elif isinstance(c, dict) and "formatted" in c:
                            formatted_list.append(c["formatted"])
                        elif isinstance(c, dict):
                            # Fallback: construct from dict fields
                            parts = []
                            if c.get("authors"):
                                authors = c["authors"]
                                if isinstance(authors, list):
                                    parts.append(", ".join(authors))
                                else:
                                    parts.append(str(authors))
                            if c.get("year"):
                                parts.append(f"({c['year']})")
                            if c.get("title"):
                                parts.append(c["title"])
                            formatted_list.append(" ".join(parts) if parts else str(c))
                        else:
                            formatted_list.append(str(c))
                    return "\n".join(formatted_list)
                elif result.get("success", True) and "formatted" in result:
                    return result["formatted"]
                return f"Error formatting citation: {result.get('error', 'Unknown error')}"
            
            else:
                return f"Error: Unknown action '{action}'. Use 'latex', 'mermaid', or 'citation'"
                
        except Exception as e:
            logger.error(f"RenderServiceTool error: {e}")
            return f"Error: {str(e)}"


def get_render_tool() -> RenderServiceTool:
    """Get a configured RenderService tool."""
    return RenderServiceTool()
