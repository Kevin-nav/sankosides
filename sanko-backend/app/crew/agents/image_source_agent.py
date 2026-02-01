"""
Image Source Agent

Dedicated agent for finding, verifying, and generating images for slides.
Combines ImageSearchTool, VisionTool, and NanoBananaImageTool to ensure
every image has proper attribution metadata.

Pipeline:
1. Search Google/Unsplash for candidates
2. Verify each with VisionTool (Gemini Vision)
3. If no good match (score < 0.7), generate with NanoBanana
4. Build proper ImageCitation metadata
5. Cache results per session
"""

import hashlib
import logging
from typing import Optional, Dict, List, Tuple
from pydantic import BaseModel, Field

from app.crew.tools.image_search_tool import ImageSearchTool, ImageSearchResult
from app.crew.tools.vision_tool import VisionTool, VisionVerification
from app.crew.tools.image_generation_tool import NanoBananaImageTool, GeneratedAsset
from app.models.schemas import ImageCitation


logger = logging.getLogger(__name__)


class ImageSourceResult(BaseModel):
    """Result from the image sourcing process."""
    image_url: str = Field(..., description="URL of the sourced image")
    image_alt: str = Field(..., description="Alt text describing the image")
    image_caption: Optional[str] = Field(None, description="Caption for the image")
    citation: ImageCitation = Field(..., description="Citation metadata for attribution")
    verification_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_method: str = Field(..., description="How image was sourced: 'search', 'generated', 'placeholder'")
    

class ImageSourceAgent:
    """
    Dedicated agent for sourcing and verifying images.
    
    This agent handles the complete image acquisition pipeline:
    1. Search multiple sources (Google, Unsplash)
    2. Verify relevance with Gemini Vision
    3. Generate fallback images if needed
    4. Build proper citation metadata
    
    Uses session-level caching to avoid duplicate searches.
    """
    
    VERIFICATION_THRESHOLD = 0.7
    MAX_SEARCH_RESULTS = 5
    
    def __init__(self, output_dir: str = "./generated_assets"):
        """
        Initialize the Image Source Agent.
        
        Args:
            output_dir: Directory for generated images
        """
        self.search_tool = ImageSearchTool()
        self.vision_tool = VisionTool()
        self.generation_tool = NanoBananaImageTool(output_dir=output_dir)
        self._cache: Dict[str, ImageSourceResult] = {}
        self._initialized = True
    
    def _cache_key(self, query: str, context: str) -> str:
        """Generate cache key from query + context."""
        return hashlib.md5(f"{query}::{context}".encode()).hexdigest()
    
    async def find_image(
        self,
        query: str,
        slide_context: str,
        allow_generation: bool = True,
    ) -> ImageSourceResult:
        """
        Find the best image for a slide.
        
        Args:
            query: What to search for (e.g., "neural network diagram")
            slide_context: Context about the slide (e.g., "explaining CNN layers")
            allow_generation: Whether to generate if no good match found
            
        Returns:
            ImageSourceResult with image URL and citation metadata
        """
        logger.info(f"[IMAGE AGENT] Finding image for: '{query}'")
        
        # Check cache first
        cache_key = self._cache_key(query, slide_context)
        if cache_key in self._cache:
            logger.info(f"[IMAGE AGENT] Cache hit for: '{query}'")
            return self._cache[cache_key]
        
        # Step 1: Search for candidates
        logger.info(f"[IMAGE AGENT] Searching for candidates...")
        candidates = await self.search_tool.search_images(query, max_results=self.MAX_SEARCH_RESULTS)
        logger.info(f"[IMAGE AGENT] Found {len(candidates)} candidates")
        
        # Step 2: Verify each candidate
        verified: List[Tuple[ImageSearchResult, VisionVerification]] = []
        expected_desc = f"{query} for {slide_context}"
        
        for i, img in enumerate(candidates):
            logger.info(f"[IMAGE AGENT] Verifying candidate {i+1}/{len(candidates)}...")
            try:
                verification = await self.vision_tool.verify_image(
                    img.url,
                    expected_description=expected_desc
                )
                logger.info(f"[IMAGE AGENT] Score: {verification.match_score:.2f} - {verification.is_match}")
                
                if verification.match_score >= self.VERIFICATION_THRESHOLD:
                    verified.append((img, verification))
            except Exception as e:
                logger.warning(f"[IMAGE AGENT] Verification failed for candidate {i+1}: {e}")
        
        # Step 3: Pick best match or generate
        result: ImageSourceResult
        
        if verified:
            # Sort by score, pick best
            verified.sort(key=lambda x: x[1].match_score, reverse=True)
            best_img, best_verification = verified[0]
            
            logger.info(
                f"[IMAGE AGENT] Selected image with score {best_verification.match_score:.2f} "
                f"from {best_img.source}"
            )
            
            result = ImageSourceResult(
                image_url=best_img.url,
                image_alt=best_verification.actual_description[:150] if best_verification.actual_description else query,
                image_caption=query,
                citation=self._build_citation_from_search(best_img),
                verification_score=best_verification.match_score,
                source_method="search",
            )
        elif allow_generation:
            # No good matches, generate image
            logger.info(f"[IMAGE AGENT] No good matches, generating image...")
            result = await self._generate_fallback(query, slide_context)
        else:
            # Return placeholder
            logger.warning(f"[IMAGE AGENT] No matches and generation disabled, using placeholder")
            result = ImageSourceResult(
                image_url="https://via.placeholder.com/800x600?text=Image+Not+Found",
                image_alt=query,
                image_caption=query,
                citation=ImageCitation(source_type="original"),
                verification_score=0.0,
                source_method="placeholder",
            )
        
        # Cache and return
        self._cache[cache_key] = result
        logger.info(f"[IMAGE AGENT] Cached result for: '{query}'")
        
        return result
    
    async def _generate_fallback(
        self,
        query: str,
        context: str
    ) -> ImageSourceResult:
        """Generate an image when search fails."""
        prompt = f"{query} - professional illustration for academic presentation about {context}"
        
        try:
            asset = await self.generation_tool.generate_concept_image(
                concept=query,
                style="professional, clean, modern illustration"
            )
            
            if asset.success and asset.file_path:
                logger.info(f"[IMAGE AGENT] Generated image: {asset.file_path}")
                
                # Check if file_path is already a URL (from R2 upload)
                if asset.file_path.startswith("http://") or asset.file_path.startswith("https://"):
                    # Already a URL from R2
                    image_url = asset.file_path
                else:
                    # Local path fallback - wrap with file://
                    logger.warning(f"[IMAGE AGENT] Image saved locally, not R2: {asset.file_path}")
                    from pathlib import Path
                    image_url = Path(asset.file_path).resolve().as_uri()
            else:
                logger.warning(f"[IMAGE AGENT] Generation failed: {asset.error}")
                image_url = "https://via.placeholder.com/800x600?text=Generation+Failed"
                
        except Exception as e:
            logger.error(f"[IMAGE AGENT] Generation error: {e}")
            image_url = "https://via.placeholder.com/800x600?text=Generation+Failed"
        
        return ImageSourceResult(
            image_url=image_url,
            image_alt=f"AI-generated illustration: {query}",
            image_caption=query,
            citation=ImageCitation(source_type="generated"),
            verification_score=1.0,  # Generated images are always "relevant"
            source_method="generated",
        )
    
    def _build_citation_from_search(self, img: ImageSearchResult) -> ImageCitation:
        """
        Build ImageCitation from search result.
        
        Determines source_type based on the source domain.
        """
        source = (img.source or "").lower()
        
        # Determine source type from domain
        if "unsplash" in source:
            source_type = "stock"
            license_info = "Unsplash License"
        elif "wikipedia" in source or "wikimedia" in source:
            source_type = "creative_commons"
            license_info = "CC BY-SA"
        elif "nasa" in source or ".gov" in source:
            source_type = "creative_commons"
            license_info = "Public Domain"
        elif "flickr" in source:
            source_type = "creative_commons"
            license_info = img.license_info or "CC License"
        elif "pexels" in source or "pixabay" in source:
            source_type = "stock"
            license_info = "Free for commercial use"
        else:
            # Default for web images
            source_type = "stock"
            license_info = img.license_info
        
        return ImageCitation(
            source_type=source_type,
            source_name=img.source or "Web",
            creator=None,  # Not always available from search
            year=None,
            license=license_info,
            url=img.url,
        )
    
    def clear_cache(self):
        """Clear the session cache."""
        self._cache.clear()
        logger.info("[IMAGE AGENT] Cache cleared")
    
    async def close(self):
        """Cleanup resources."""
        if hasattr(self.search_tool, '_http_client'):
            await self.search_tool._http_client.aclose()
        await self.vision_tool.close()
        logger.info("[IMAGE AGENT] Resources closed")
