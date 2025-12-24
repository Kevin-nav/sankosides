"""
Vision Tool

Verifies that an image URL matches its intended description.
Uses Gemini 3 Flash Preview for fast, accurate vision analysis.

Usage:
    tool = VisionTool(api_key="...")
    result = await tool.verify_image(
        image_url="https://example.com/neural-net.png",
        expected_description="A diagram of a neural network with 3 layers"
    )
    print(f"Match score: {result.match_score}")  # 0.0 - 1.0
"""

import httpx
import base64
from typing import Optional, List
from pydantic import BaseModel, Field

from google import genai
from google.genai import types

from app.config import settings


class VisionVerification(BaseModel):
    """Result of image verification."""
    match_score: float = Field(..., ge=0.0, le=1.0, description="How well image matches description (0-1)")
    is_match: bool = Field(..., description="Whether image is considered a match (score >= 0.7)")
    actual_description: str = Field(..., description="What the model actually sees in the image")
    reasoning: str = Field(..., description="Why the score was given")
    issues: List[str] = Field(default_factory=list, description="Any problems detected")


class VisionTool:
    """
    Tool for verifying image relevance using Gemini 3 Flash Preview.
    
    This is used by the Planner agent to verify that sourced images
    actually match their intended descriptions before including them
    in the presentation.
    """
    
    MATCH_THRESHOLD = 0.7  # Score >= this is considered a match
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.gemini_api_key
        self.client = genai.Client(api_key=self.api_key)
        self._http_client = httpx.AsyncClient(timeout=30.0)
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """Download image from URL."""
        try:
            response = await self._http_client.get(url)
            response.raise_for_status()
            return response.content
        except Exception as e:
            print(f"Failed to download image from {url}: {e}")
            return None
    
    def _get_mime_type(self, url: str, content: bytes) -> str:
        """Determine MIME type from URL or content."""
        url_lower = url.lower()
        if ".png" in url_lower:
            return "image/png"
        elif ".jpg" in url_lower or ".jpeg" in url_lower:
            return "image/jpeg"
        elif ".gif" in url_lower:
            return "image/gif"
        elif ".webp" in url_lower:
            return "image/webp"
        elif ".svg" in url_lower:
            return "image/svg+xml"
        else:
            # Default to JPEG if can't determine
            return "image/jpeg"
    
    async def verify_image(
        self,
        image_url: str,
        expected_description: str,
    ) -> VisionVerification:
        """
        Verify that an image matches its expected description.
        
        Args:
            image_url: URL of the image to verify
            expected_description: What the image should contain
            
        Returns:
            VisionVerification with match score and analysis
        """
        # Download the image
        image_data = await self.download_image(image_url)
        
        if not image_data:
            return VisionVerification(
                match_score=0.0,
                is_match=False,
                actual_description="Failed to download image",
                reasoning="Could not retrieve image from URL",
                issues=["Image download failed"]
            )
        
        # Encode for Gemini
        image_b64 = base64.standard_b64encode(image_data).decode("utf-8")
        mime_type = self._get_mime_type(image_url, image_data)
        
        # Build verification prompt
        prompt = f"""Analyze this image and compare it to the expected description.

EXPECTED DESCRIPTION: {expected_description}

Your task:
1. Describe what you actually see in the image
2. Compare it to the expected description
3. Give a match score from 0.0 to 1.0
4. List any issues or mismatches

Respond in this exact JSON format:
{{
    "actual_description": "What you see in the image",
    "match_score": 0.85,
    "reasoning": "Why you gave this score",
    "issues": ["Issue 1", "Issue 2"]
}}

Be strict but fair. A perfect match is 1.0. Minor differences are 0.8-0.9. 
Somewhat related is 0.5-0.7. Not related is 0.0-0.4."""

        try:
            # Call Gemini 3 Flash with HIGH thinking for careful analysis
            response = self.client.models.generate_content(
                model=settings.model_flash,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text=prompt),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=mime_type,
                                    data=image_b64,
                                )
                            )
                        ]
                    )
                ],
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(
                        thinking_level=settings.thinking_level_high
                    )
                )
            )
            
            response_text = response.text
            
            # Parse JSON response
            import json
            import re
            
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group())
                score = float(data.get("match_score", 0.5))
                return VisionVerification(
                    match_score=score,
                    is_match=score >= self.MATCH_THRESHOLD,
                    actual_description=data.get("actual_description", ""),
                    reasoning=data.get("reasoning", ""),
                    issues=data.get("issues", [])
                )
            
            # Fallback if parsing fails
            return VisionVerification(
                match_score=0.5,
                is_match=False,
                actual_description=response_text[:200],
                reasoning="Could not parse structured response",
                issues=["Response parsing failed"]
            )
            
        except Exception as e:
            return VisionVerification(
                match_score=0.0,
                is_match=False,
                actual_description="Error during analysis",
                reasoning=str(e),
                issues=[f"Vision analysis error: {str(e)}"]
            )
    
    async def describe_image(self, image_url: str) -> str:
        """
        Get a description of an image without comparison.
        Useful for understanding what an image contains.
        """
        image_data = await self.download_image(image_url)
        
        if not image_data:
            return "Failed to download image"
        
        image_b64 = base64.standard_b64encode(image_data).decode("utf-8")
        mime_type = self._get_mime_type(image_url, image_data)
        
        try:
            response = self.client.models.generate_content(
                model=settings.model_flash,
                contents=[
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(text="Describe this image in detail. Focus on the main subject, style, and any text visible."),
                            types.Part(
                                inline_data=types.Blob(
                                    mime_type=mime_type,
                                    data=image_b64,
                                )
                            )
                        ]
                    )
                ],
            )
            return response.text
        except Exception as e:
            return f"Error: {str(e)}"
    
    async def close(self):
        """Close HTTP client."""
        await self._http_client.aclose()
