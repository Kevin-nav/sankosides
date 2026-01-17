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
    
    Note: Uses lazy client initialization to handle cases where
    the client is used across different event loops (e.g., when
    called from ThreadPoolExecutor with new event loops).
    """
    
    def __init__(self, base_url: str = "http://localhost:3001"):
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None
    
    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for current event loop."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client
    
    async def health_check(self) -> bool:
        """Check if the render service is running."""
        try:
            response = await self._get_client().get(f"{self.base_url}/health")
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
            response = await self._get_client().post(
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
            response = await self._get_client().post(
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
            response = await self._get_client().post(
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
            response = await self._get_client().post(
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
    
    async def render_html_to_png(
        self,
        html: str,
        width: int = 1280,
        height: int = 720,
    ) -> Dict[str, Any]:
        """
        Render HTML content to a PNG screenshot.
        
        Uses Puppeteer on the render service to capture a screenshot
        of the rendered HTML. Used by Visual QA for slide grading.
        
        Args:
            html: Complete HTML document to render
            width: Viewport width in pixels (default 1280 for 16:9)
            height: Viewport height in pixels (default 720)
            
        Returns:
            Dict with 'png_base64' on success, 'error' on failure
        """
        try:
            response = await self._get_client().post(
                f"{self.base_url}/render/screenshot",
                json={"html": html, "width": width, "height": height},
                timeout=60.0,  # Screenshots can take longer
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# Convenience function
async def get_render_client() -> RenderServiceClient:
    """Get a configured render service client."""
    return RenderServiceClient()
