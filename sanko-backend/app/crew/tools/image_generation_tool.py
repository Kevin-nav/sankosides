"""
Nano Banana Pro Image Generation Tool

Generates visual assets using Gemini 3 Pro Image (Nano Banana Pro).
Supports reference image injection for brand consistency.

Usage:
    tool = NanoBananaImageTool(api_key="...")
    result = await tool.generate_asset(
        prompt="A modern office workspace with plants",
        style="minimalist photography"
    )
    print(f"Generated: {result.file_path}")
"""

import os
import base64
from datetime import datetime
from typing import Optional, List
from pathlib import Path
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from app.core.config import settings
from app.clients.gemini.retry import gemini_retry
from app.core.logging import get_logger

logger = get_logger(__name__)


class GeneratedAsset(BaseModel):
    """Result of image generation."""
    success: bool = Field(..., description="Whether generation succeeded")
    file_path: Optional[str] = Field(None, description="Path to saved image file")
    file_name: Optional[str] = Field(None, description="Generated filename")
    prompt_used: str = Field(..., description="The prompt that was used")
    mime_type: str = Field(default="image/png", description="Image MIME type")
    error: Optional[str] = Field(None, description="Error message if failed")


class NanoBananaImageTool:
    """
    Tool for generating visual assets using Nano Banana Pro (Gemini 3 Pro Image).
    
    This is used by agents to create:
    - Background images for slides
    - Concept visualizations
    - Diagrams and illustrations
    - Brand-consistent assets (using reference images)
    
    Prompt Structure (for best results):
    - Subject: Who/What is the main focus
    - Composition: Framing, angle, arrangement
    - Action: What is happening (if applicable)
    - Location: Setting/environment
    - Style: Aesthetic, artistic style
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        output_dir: str = "./generated_assets"
    ):
        self.api_key = api_key or settings.gemini_api_key
        self.client = genai.Client(api_key=self.api_key)
        self.output_dir = Path(output_dir).resolve()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        # Lazy-loaded R2 storage service
        self._storage = None
    
    def _get_storage(self):
        """Get R2 storage service (lazy-loaded)."""
        if self._storage is None:
            from app.services.storage import get_storage_service
            self._storage = get_storage_service()
        return self._storage
    
    def _build_structured_prompt(
        self,
        subject: str,
        style: str = "professional",
        composition: Optional[str] = None,
        action: Optional[str] = None,
        location: Optional[str] = None,
        text_to_render: Optional[str] = None,
    ) -> str:
        """
        Build a structured prompt following Nano Banana Pro best practices.
        
        The model performs best with structured prompts that clearly
        define Subject, Composition, Action, Location, and Style.
        """
        parts = []
        
        # Subject (required)
        parts.append(f"Subject: {subject}")
        
        # Composition (optional but recommended)
        if composition:
            parts.append(f"Composition: {composition}")
        
        # Action (optional)
        if action:
            parts.append(f"Action: {action}")
        
        # Location (optional)
        if location:
            parts.append(f"Location: {location}")
        
        # Style (required for consistency)
        parts.append(f"Style: {style}")
        
        # Text rendering (Nano Banana Pro handles text well)
        if text_to_render:
            parts.append(f"Text in image: \"{text_to_render}\" (render clearly and legibly)")
        
        return "\n".join(parts)
    
    async def generate_asset(
        self,
        prompt: str,
        reference_images: Optional[List[str]] = None,
        style: str = "professional, high quality",
        upload_to_r2: bool = True,
    ) -> GeneratedAsset:
        """
        Generate a visual asset from a text prompt.
        
        Args:
            prompt: Description of what to generate
            reference_images: Optional list of image paths for style reference (up to 14)
            style: Artistic style to apply
            upload_to_r2: Whether to upload to R2 (True) or save locally (False)
            
        Returns:
            GeneratedAsset with file path/URL and metadata
        """
        # Build full prompt with style
        full_prompt = f"{prompt}\n\nStyle: {style}"
        
        try:
            # Build content parts
            content_parts = [types.Part(text=full_prompt)]
            
            # Add reference images if provided (up to 14 for brand consistency)
            if reference_images:
                for i, img_path in enumerate(reference_images[:14]):
                    try:
                        with open(img_path, "rb") as f:
                            img_data = base64.standard_b64encode(f.read()).decode("utf-8")
                        
                        # Determine MIME type
                        path_lower = img_path.lower()
                        if ".png" in path_lower:
                            mime = "image/png"
                        elif ".jpg" in path_lower or ".jpeg" in path_lower:
                            mime = "image/jpeg"
                        else:
                            mime = "image/png"
                        
                        content_parts.append(
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=mime,
                                    data=img_data,
                                )
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to load reference image {img_path}: {e}")
            
            # Wrap API call with retry for transient errors (503, 429)
            @gemini_retry(max_attempts=4, min_wait=2, max_wait=60)
            def call_image_api():
                return self.client.models.generate_content(
                    model=settings.model_image,  # gemini-3-pro-image-preview
                    contents=[
                        types.Content(
                            role="user",
                            parts=content_parts
                        )
                    ],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    )
                )
            
            # Call Nano Banana Pro (Gemini 3 Pro Image) with retry
            logger.info(f"[IMAGE GEN] Generating image with prompt: {prompt[:100]}...")
            response = call_image_api()
            
            # Extract generated image
            for candidate in response.candidates:
                for part in candidate.content.parts:
                    if part.inline_data:
                        # Google GenAI SDK returns raw bytes, NOT base64 encoded
                        # Using the data directly - no decode needed
                        image_data = part.inline_data.data
                        
                        # Generate filename
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename = f"generated_{timestamp}.png"
                        
                        # Try to upload to R2 for production use
                        if upload_to_r2:
                            try:
                                storage = self._get_storage()
                                # upload_file returns tuple: (file_hash, r2_key, was_cached)
                                file_hash, r2_key, was_cached = await storage.upload_file(
                                    file_data=image_data,
                                    original_filename=filename,
                                    content_type="image/png",
                                )
                                
                                # Get public URL
                                public_url = storage.get_public_url(r2_key)
                                if not public_url:
                                    # Fallback to pre-signed URL (1 hour)
                                    public_url = await storage.get_presigned_url(
                                        r2_key, 
                                        expires_in=3600
                                    )
                                
                                logger.info(f"[IMAGE GEN] Uploaded to R2: {public_url}")
                                
                                return GeneratedAsset(
                                    success=True,
                                    file_path=public_url,  # R2 URL
                                    file_name=filename,
                                    prompt_used=full_prompt,
                                    mime_type="image/png",
                                )
                            except Exception as upload_error:
                                # Fall back to local save
                                logger.warning(f"[IMAGE GEN] R2 upload failed, saving locally: {upload_error}")
                        
                        # Local fallback
                        file_path = self.output_dir / filename
                        with open(file_path, "wb") as f:
                            f.write(image_data)
                        
                        logger.info(f"[IMAGE GEN] Saved locally: {file_path}")
                        
                        return GeneratedAsset(
                            success=True,
                            file_path=str(file_path),
                            file_name=filename,
                            prompt_used=full_prompt,
                            mime_type="image/png",
                        )
            
            return GeneratedAsset(
                success=False,
                prompt_used=full_prompt,
                error="No image was generated. Model may have refused the prompt."
            )
            
        except Exception as e:
            logger.error(f"[IMAGE GEN] Generation failed: {e}")
            return GeneratedAsset(
                success=False,
                prompt_used=full_prompt,
                error=str(e)
            )
    
    async def generate_slide_background(
        self,
        theme: str,
        mood: str = "professional",
        color_hints: Optional[List[str]] = None,
    ) -> GeneratedAsset:
        """
        Generate a background image suitable for presentation slides.
        
        Args:
            theme: The presentation theme (e.g., "technology", "nature", "abstract")
            mood: The emotional tone (e.g., "professional", "creative", "calm")
            color_hints: Optional colors to incorporate
            
        Returns:
            GeneratedAsset with the background image
        """
        color_text = ""
        if color_hints:
            color_text = f" incorporating these colors: {', '.join(color_hints)}"
        
        prompt = self._build_structured_prompt(
            subject=f"Abstract background pattern for {theme} presentation",
            composition="Full frame, no focal point, suitable as background",
            style=f"{mood}, subtle, not distracting, high resolution{color_text}",
            location="Abstract/conceptual space"
        )
        
        return await self.generate_asset(
            prompt=prompt,
            style="subtle, professional, suitable as slide background"
        )
    
    async def generate_concept_image(
        self,
        concept: str,
        style: str = "modern illustration",
    ) -> GeneratedAsset:
        """
        Generate a concept visualization for explaining ideas.
        
        Args:
            concept: The concept to visualize (e.g., "machine learning", "teamwork")
            style: Visual style for the illustration
            
        Returns:
            GeneratedAsset with the concept image
        """
        prompt = self._build_structured_prompt(
            subject=f"Visual metaphor representing {concept}",
            composition="Centered, clean, easy to understand",
            style=style,
        )
        
        return await self.generate_asset(
            prompt=prompt,
            style=style
        )
    
    async def generate_for_slide(
        self,
        subject: str,
        slide_context: str = "",
        style_preset: str = "academic",
    ) -> GeneratedAsset:
        """
        Generate an image specifically optimized for presentation slides.
        
        This is the primary method for the AI-first image strategy.
        
        Args:
            subject: What the image should depict
            slide_context: Additional context about the slide/presentation
            style_preset: One of 'academic', 'corporate', 'creative', 'minimal', 'technical'
            
        Returns:
            GeneratedAsset with the generated image URL
        """
        # Style presets optimized for presentations
        style_map = {
            "academic": "professional, clean, educational, suitable for academic presentation, modern illustration",
            "corporate": "professional, business-appropriate, polished, corporate aesthetic, clean lines",
            "creative": "vibrant, artistic, visually engaging, modern design, creative illustration",
            "minimal": "minimalist, clean composition, simple, lots of whitespace, subtle colors",
            "technical": "technical diagram style, informative, precise, engineering aesthetic",
        }
        
        style = style_map.get(style_preset, style_map["academic"])
        
        # Build optimized prompt for slides
        prompt_parts = [
            f"Subject: {subject}",
            "Purpose: Professional presentation slide image",
            "Composition: Clean, centered focal point, balanced layout",
        ]
        
        if slide_context:
            prompt_parts.append(f"Context: {slide_context}")
        
        prompt_parts.extend([
            "Requirements:",
            "- High resolution (1600x900 or similar widescreen)",
            "- No text overlays or watermarks",
            "- Suitable for projection on large screens",
            "- Professional quality",
        ])
        
        full_prompt = "\n".join(prompt_parts)
        
        return await self.generate_asset(
            prompt=full_prompt,
            style=style,
            upload_to_r2=True,
        )

