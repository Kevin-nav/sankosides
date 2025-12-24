"""
CrewAI Tool Wrappers

Provides CrewAI-compatible BaseTool wrappers for our custom tools.
This allows agents to invoke tools via function calling.

The wrappers delegate to existing tool implementations.
"""

import asyncio
from typing import Optional, TYPE_CHECKING

from crewai.tools import BaseTool
from pydantic import Field

if TYPE_CHECKING:
    from app.tools.vision_tool import VisionTool
    from app.tools.image_generation_tool import NanoBananaImageTool
    from app.tools.image_search_tool import ImageSearchTool
    from app.tools.academic_search_tool import AcademicSearchTool


class VisionVerificationTool(BaseTool):
    """
    CrewAI-compatible tool for verifying images match descriptions.
    
    Delegates to VisionTool for actual implementation.
    """
    name: str = "verify_image"
    description: str = """Verifies that an image URL matches an expected description.
Use when you need to confirm an image is appropriate for a slide.
Returns a match score (0-1) and whether the image is acceptable.

Input format: JSON with 'image_url' and 'expected_description' keys.
Example: {"image_url": "https://...", "expected_description": "Neural network diagram"}"""
    
    # The actual tool implementation (injected)
    _vision_tool: Optional["VisionTool"] = None
    
    def set_tool(self, tool: "VisionTool"):
        """Inject the actual tool implementation."""
        self._vision_tool = tool
    
    def _run(self, image_url: str, expected_description: str = "") -> str:
        """
        Verify an image matches its expected description.
        """
        if not self._vision_tool:
            return "Error: VisionTool not configured"
        
        try:
            # Run async tool in sync context
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            
            result = loop.run_until_complete(
                self._vision_tool.verify_image(image_url, expected_description)
            )
            
            if result.is_match:
                return f"✅ Image VERIFIED (score: {result.match_score:.2f}). Description: {result.actual_description}"
            else:
                return f"❌ Image REJECTED (score: {result.match_score:.2f}). Issues: {', '.join(result.issues)}"
                
        except Exception as e:
            return f"Error verifying image: {str(e)}"


class ImageGenerationTool(BaseTool):
    """
    CrewAI-compatible tool for generating images with Nano Banana Pro.
    
    Use this for creating custom visuals like diagrams, concepts, and graphics.
    NOT for finding existing photos - use ImageSearchTool for that.
    """
    name: str = "generate_image"
    description: str = """GENERATES custom visual assets using AI (Nano Banana Pro / Gemini 3 Pro Image).

Best for:
- Diagrams and flowcharts
- Concept illustrations
- Custom graphics and infographics
- Abstract backgrounds
- Any visual that doesn't exist and needs to be CREATED

NOT for: Real photographs or existing stock images (use search_images instead).

Prompt should follow this structure for best results:
- Subject: What is the main focus
- Composition: Framing and arrangement
- Style: Visual aesthetic (e.g., "modern", "minimalist", "corporate")

Input: A detailed prompt describing the desired image."""
    
    _image_gen_tool: Optional["NanoBananaImageTool"] = None
    
    def set_tool(self, tool: "NanoBananaImageTool"):
        """Inject the actual tool implementation."""
        self._image_gen_tool = tool
    
    def _run(self, prompt: str) -> str:
        """
        Generate a custom image from prompt.
        """
        if not self._image_gen_tool:
            return "Error: NanoBananaImageTool not configured"
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            
            result = loop.run_until_complete(
                self._image_gen_tool.generate_asset(
                    prompt=prompt,
                    style="professional, high quality presentation graphic"
                )
            )
            
            if result.success:
                return f"✅ Generated image at: {result.file_path}"
            else:
                return f"❌ Generation failed: {result.error}"
                
        except Exception as e:
            return f"Error generating image: {str(e)}"


class ImageSearchCrewTool(BaseTool):
    """
    CrewAI-compatible tool for searching existing images.
    
    Use this for finding real photographs and stock images.
    NOT for creating custom graphics - use generate_image for that.
    """
    name: str = "search_images"
    description: str = """Searches for EXISTING photos and images from Unsplash and Google.

Best for:
- Real photographs
- Stock images
- Photos of real objects, places, or people

NOT for: Custom diagrams, concepts, or graphics (use generate_image instead).

Input: Search query string describing what image you need.
Example: "modern office workspace" or "team collaboration meeting\""""
    
    _image_search_tool: Optional["ImageSearchTool"] = None
    
    def set_tool(self, tool: "ImageSearchTool"):
        """Inject the actual tool implementation."""
        self._image_search_tool = tool
    
    def _run(self, query: str, max_results: int = 3) -> str:
        """
        Search for images matching the query.
        """
        if not self._image_search_tool:
            return "Error: ImageSearchTool not configured"
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            
            results = loop.run_until_complete(
                self._image_search_tool.search_images(query, max_results=max_results)
            )
            
            if results:
                output_lines = ["Found images:"]
                for i, r in enumerate(results, 1):
                    output_lines.append(f"{i}. {r.url} (Source: {r.source})")
                return "\n".join(output_lines)
            else:
                return "No images found for this query. Consider using generate_image to create a custom visual."
                
        except Exception as e:
            return f"Error searching images: {str(e)}"


class AcademicSearchCrewTool(BaseTool):
    """
    CrewAI-compatible tool for finding academic citations.
    
    Searches CrossRef, Semantic Scholar, and ArXiv for verified citations.
    """
    name: str = "search_citations"
    description: str = """Searches academic databases for verified citations.

Use when you need:
- Academic papers to cite claims
- Research to support content
- Verified sources with DOIs

Returns: Citation metadata including title, authors, year, DOI.

Input: Search query for academic content.
Example: "machine learning image classification accuracy\""""
    
    _search_tool: Optional["AcademicSearchTool"] = None
    
    def set_tool(self, tool: "AcademicSearchTool"):
        """Inject the actual tool implementation."""
        self._search_tool = tool
    
    def _run(self, query: str, max_results: int = 2) -> str:
        """
        Search for academic citations.
        """
        if not self._search_tool:
            return "Error: AcademicSearchTool not configured"
        
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import nest_asyncio
                nest_asyncio.apply()
            
            results = loop.run_until_complete(
                self._search_tool.search(query, max_results=max_results)
            )
            
            if results:
                output_lines = ["Found citations:"]
                for i, c in enumerate(results, 1):
                    authors = ", ".join(c.authors[:2]) if c.authors else "Unknown"
                    if len(c.authors) > 2:
                        authors += " et al."
                    output_lines.append(f"{i}. \"{c.title}\" by {authors} ({c.year})")
                    if c.doi:
                        output_lines.append(f"   DOI: {c.doi}")
                return "\n".join(output_lines)
            else:
                return "No academic citations found for this query."
                
        except Exception as e:
            return f"Error searching citations: {str(e)}"


def create_crewai_tools(
    vision_tool: "VisionTool",
    image_gen_tool: "NanoBananaImageTool", 
    image_search_tool: "ImageSearchTool",
    search_tool: "AcademicSearchTool",
) -> list:
    """
    Create all CrewAI tool wrappers with injected implementations.
    
    Returns a list of tools ready to pass to CrewAI agents.
    """
    vision = VisionVerificationTool()
    vision.set_tool(vision_tool)
    
    image_gen = ImageGenerationTool()
    image_gen.set_tool(image_gen_tool)
    
    image_search = ImageSearchCrewTool()
    image_search.set_tool(image_search_tool)
    
    academic = AcademicSearchCrewTool()
    academic.set_tool(search_tool)
    
    return [vision, image_gen, image_search, academic]
