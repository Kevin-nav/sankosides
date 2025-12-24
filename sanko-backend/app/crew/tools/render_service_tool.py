"""
RenderService CrewAI Tool

Wraps the RenderService client as a CrewAI-compatible tool.
Allows agents to render LaTeX equations, Mermaid diagrams, and format citations.
"""

import asyncio
from typing import Optional, List, Dict, Any
from crewai.tools import BaseTool
from pydantic import Field

from app.clients.render import RenderServiceClient
from app.core.logging import get_logger

logger = get_logger(__name__)


class RenderServiceTool(BaseTool):
    """
    CrewAI-compatible tool for rendering STEM content.
    
    Provides access to the Node.js rendering microservice for:
    - LaTeX → SVG (math equations)
    - Mermaid → SVG (diagrams, flowcharts)
    - Citation formatting (APA, IEEE, Harvard, Chicago)
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
    
    _client: Optional[RenderServiceClient] = None
    
    def _get_client(self) -> RenderServiceClient:
        """Get or create the render service client."""
        if self._client is None:
            self._client = RenderServiceClient()
        return self._client
    
    def _run(
        self,
        action: str,
        content: Optional[str] = None,
        citation: Optional[Dict[str, Any]] = None,
        citations: Optional[List[Dict[str, Any]]] = None,
        style: str = "apa",
    ) -> str:
        """
        Execute a render action.
        
        Args:
            action: "latex", "mermaid", or "citation"
            content: LaTeX or Mermaid code (for latex/mermaid actions)
            citation: Single citation dict (for citation action)
            citations: List of citations (for batch citation formatting)
            style: Citation style (apa, ieee, harvard, chicago)
            
        Returns:
            Rendered result as string (SVG for equations/diagrams, formatted text for citations)
        """
        # Run async code in sync context
        return asyncio.run(self._async_run(action, content, citation, citations, style))
    
    async def _async_run(
        self,
        action: str,
        content: Optional[str],
        citation: Optional[Dict[str, Any]],
        citations: Optional[List[Dict[str, Any]]],
        style: str,
    ) -> str:
        """Async implementation of the render action."""
        client = self._get_client()
        
        try:
            if action == "latex":
                if not content:
                    return "Error: 'content' is required for latex rendering"
                result = await client.render_latex(content)
                if result.get("success", True) and "svg" in result:
                    return result["svg"]
                return f"Error rendering LaTeX: {result.get('error', 'Unknown error')}"
            
            elif action == "mermaid":
                if not content:
                    return "Error: 'content' is required for mermaid rendering"
                result = await client.render_mermaid(content)
                if result.get("success", True) and "svg" in result:
                    return result["svg"]
                return f"Error rendering Mermaid: {result.get('error', 'Unknown error')}"
            
            elif action == "citation":
                if citations:
                    result = await client.format_citations(citations, style)
                elif citation:
                    result = await client.format_citation(citation, style)
                else:
                    return "Error: 'citation' or 'citations' is required"
                
                if result.get("success", True) and "citations" in result:
                    return "\n".join(result["citations"])
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
