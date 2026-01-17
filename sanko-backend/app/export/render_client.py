"""
Render Service Client

Client for communicating with the sanko-render-service to convert
SVG diagrams to PNG for embedding in exports.
"""

import base64
from typing import Optional, Tuple
import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default render service URL
RENDER_SERVICE_URL = getattr(settings, 'render_service_url', 'http://localhost:3001')


class RenderServiceClient:
    """
    Client for the sanko-render-service.
    
    Provides methods for converting SVG to PNG for PowerPoint embedding.
    """
    
    def __init__(self, base_url: str = RENDER_SERVICE_URL):
        self.base_url = base_url.rstrip('/')
        self.timeout = 30.0  # 30 second timeout
    
    async def svg_to_png(
        self,
        svg: str,
        width: int = 800,
        height: int = 600,
        scale: int = 2,
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Convert SVG to high-resolution PNG.
        
        Args:
            svg: SVG content as string
            width: Target width in pixels
            height: Target height in pixels
            scale: Scale factor for high-res (2 = 2x resolution)
            
        Returns:
            Tuple of (PNG bytes, error message if failed)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/render/svg-to-png",
                    json={
                        "svg": svg,
                        "width": width,
                        "height": height,
                        "scale": scale,
                    },
                )
                
                if response.status_code != 200:
                    error = response.json().get("error", "Unknown error")
                    logger.warning(f"Render service error: {error}")
                    return None, error
                
                data = response.json()
                if not data.get("success"):
                    return None, data.get("error", "Conversion failed")
                
                # Decode base64 PNG
                png_base64 = data.get("png_base64")
                if not png_base64:
                    return None, "No PNG data returned"
                
                png_bytes = base64.b64decode(png_base64)
                logger.debug(f"Converted SVG to PNG: {len(png_bytes)} bytes")
                return png_bytes, None
                
        except httpx.ConnectError:
            error = f"Cannot connect to render service at {self.base_url}"
            logger.error(error)
            return None, error
        except Exception as e:
            logger.error(f"SVG to PNG conversion failed: {e}")
            return None, str(e)
    
    async def render_mermaid_to_png(
        self,
        diagram: str,
        width: int = 800,
        height: int = 600,
        scale: int = 2,
        theme: str = "default",
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Render Mermaid diagram to PNG in one step.
        
        First renders Mermaid to SVG, then converts to PNG.
        
        Args:
            diagram: Mermaid diagram code
            width: Target width
            height: Target height
            scale: Scale factor
            theme: Mermaid theme
            
        Returns:
            Tuple of (PNG bytes, error message if failed)
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                # Step 1: Mermaid → SVG
                svg_response = await client.post(
                    f"{self.base_url}/render/mermaid",
                    json={"diagram": diagram, "theme": theme},
                )
                
                if svg_response.status_code != 200:
                    error = svg_response.json().get("error", "Mermaid render failed")
                    return None, error
                
                svg_data = svg_response.json()
                if not svg_data.get("success"):
                    return None, svg_data.get("error", "Mermaid render failed")
                
                svg = svg_data.get("svg")
                if not svg:
                    return None, "No SVG returned from Mermaid render"
                
                # Step 2: SVG → PNG
                return await self.svg_to_png(svg, width, height, scale)
                
        except Exception as e:
            logger.error(f"Mermaid to PNG failed: {e}")
            return None, str(e)
    
    async def html_to_pdf(
        self,
        slides_html: list,
        format: str = "16:9",
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Convert HTML slides to PDF.
        
        Args:
            slides_html: List of HTML strings, one per slide
            format: Page format (16:9, 4:3, A4, Letter)
            
        Returns:
            Tuple of (PDF bytes, error message if failed)
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:  # Longer timeout for PDF
                response = await client.post(
                    f"{self.base_url}/render/html-to-pdf",
                    json={
                        "slides": slides_html,
                        "format": format,
                        "margin": 0,
                        "landscape": True,
                    },
                )
                
                if response.status_code != 200:
                    error = response.json().get("error", "Unknown error")
                    logger.warning(f"Render service error: {error}")
                    return None, error
                
                data = response.json()
                if not data.get("success"):
                    return None, data.get("error", "PDF generation failed")
                
                # Decode base64 PDF
                pdf_base64 = data.get("pdf_base64")
                if not pdf_base64:
                    return None, "No PDF data returned"
                
                pdf_bytes = base64.b64decode(pdf_base64)
                logger.info(f"Generated PDF: {len(pdf_bytes)} bytes, {data.get('pages', 1)} pages")
                return pdf_bytes, None
                
        except httpx.ConnectError:
            error = f"Cannot connect to render service at {self.base_url}"
            logger.error(error)
            return None, error
        except Exception as e:
            logger.error(f"HTML to PDF conversion failed: {e}")
            return None, str(e)
    
    async def health_check(self) -> bool:
        """Check if render service is available."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False


# Singleton instance
_client: Optional[RenderServiceClient] = None


def get_render_client() -> RenderServiceClient:
    """Get or create the render service client."""
    global _client
    if _client is None:
        _client = RenderServiceClient()
    return _client


async def svg_to_png(
    svg: str,
    width: int = 800,
    height: int = 600,
    scale: int = 2,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Convert SVG to PNG using the render service.
    
    Convenience function that uses the singleton client.
    """
    return await get_render_client().svg_to_png(svg, width, height, scale)
