"""
Render Service Client

Python client for the Node.js rendering microservice.
Handles LaTeX→SVG, Mermaid→SVG, and citation formatting.

Usage:
    client = RenderServiceClient()
    svg = await client.render_latex("E = mc^2")
    citation = await client.format_citation({...})
"""

import httpx
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from app.core.config import settings


class RenderServiceClient:
    """
    Client for the SankoSlides rendering microservice.
    
    This service handles deterministic rendering tasks that
    should not be done by AI (to avoid hallucination).
    """
    
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self._client = httpx.AsyncClient(timeout=30.0)
    
    async def health_check(self) -> bool:
        """Check if the render service is running."""
        try:
            response = await self._client.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False
    
    async def render_latex(
        self,
        latex: str,
        display: bool = True,
    ) -> Dict[str, Any]:
        """
        Render LaTeX to SVG.
        
        Args:
            latex: LaTeX string (with or without $$ delimiters)
            display: Whether to use display mode (default True)
            
        Returns:
            Dict with 'svg', 'width', 'height' on success
        """
        try:
            response = await self._client.post(
                f"{self.base_url}/render/latex",
                json={"latex": latex, "display": display},
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def render_mermaid(self, diagram: str) -> Dict[str, Any]:
        """
        Render Mermaid diagram to SVG.
        
        Args:
            diagram: Mermaid diagram code
            
        Returns:
            Dict with 'svg' on success
        """
        try:
            response = await self._client.post(
                f"{self.base_url}/render/mermaid",
                json={"diagram": diagram},
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def format_citation(
        self,
        citation: Dict[str, Any],
        style: str = "apa",
    ) -> Dict[str, Any]:
        """
        Format a single citation using citation-js.
        
        Args:
            citation: Citation metadata (author, year, title, doi, url, source)
            style: Citation style (apa, ieee, harvard, chicago)
            
        Returns:
            Dict with 'formatted' string
        """
        return await self.format_citations([citation], style)
    
    async def format_citations(
        self,
        citations: List[Dict[str, Any]],
        style: str = "apa",
    ) -> Dict[str, Any]:
        """
        Format multiple citations.
        
        Args:
            citations: List of citation metadata
            style: Citation style
            
        Returns:
            Dict with 'citations' array of formatted strings
        """
        try:
            response = await self._client.post(
                f"{self.base_url}/render/citation",
                json={"citations": citations, "style": style},
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def batch_render(
        self,
        latex: List[str] = None,
        diagrams: List[str] = None,
        citations: List[Dict[str, Any]] = None,
        style: str = "apa",
    ) -> Dict[str, Any]:
        """
        Batch render multiple elements.
        
        Useful for processing all STEM elements in a slide at once.
        
        Args:
            latex: List of LaTeX strings
            diagrams: List of Mermaid diagrams
            citations: List of citation metadata
            style: Citation style
            
        Returns:
            Dict with results for each type
        """
        try:
            response = await self._client.post(
                f"{self.base_url}/render/batch",
                json={
                    "latex": latex or [],
                    "diagrams": diagrams or [],
                    "citations": citations or [],
                    "style": style,
                },
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


# Convenience function
async def get_render_client() -> RenderServiceClient:
    """Get a configured render service client."""
    return RenderServiceClient()
