"""
Gemini API Helper Functions

Token extraction, part building, and other utilities for Gemini API.
Extracted from interactions.py for better modularity.
"""

from typing import Dict, Any
from google.genai import types

from app.core.logging import get_logger

logger = get_logger(__name__)


def extract_token_usage(response) -> Dict[str, int]:
    """
    Extract token usage from API response.
    
    Handles both response types:
    - generate_content: usage_metadata with prompt_token_count, candidates_token_count
    - interactions.create: usage with input_tokens, output_tokens, total_thought_tokens
    
    Args:
        response: API response object
        
    Returns:
        Dict with token counts
    """
    tokens = {
        "input_tokens": 0,
        "output_tokens": 0,
        "thinking_tokens": 0,
        "cached_tokens": 0,
        "total_tokens": 0,
    }
    
    # Interactions API uses 'usage' attribute with 'total_*' prefixed fields
    if hasattr(response, 'usage') and response.usage:
        usage = response.usage
        tokens["input_tokens"] = getattr(usage, 'total_input_tokens', 0) or 0
        tokens["output_tokens"] = getattr(usage, 'total_output_tokens', 0) or 0
        tokens["thinking_tokens"] = getattr(usage, 'total_thought_tokens', 0) or 0
        tokens["cached_tokens"] = getattr(usage, 'cached_tokens', 0) or 0
    
    # generate_content uses 'usage_metadata' attribute
    elif hasattr(response, 'usage_metadata') and response.usage_metadata:
        meta = response.usage_metadata
        tokens["input_tokens"] = getattr(meta, 'prompt_token_count', 0) or 0
        tokens["output_tokens"] = getattr(meta, 'candidates_token_count', 0) or 0
        tokens["thinking_tokens"] = getattr(meta, 'thoughts_token_count', 0) or 0
        tokens["cached_tokens"] = getattr(meta, 'cached_content_token_count', 0) or 0
    
    # Fallback: check metadata dict
    elif hasattr(response, 'metadata') and response.metadata:
        meta = response.metadata
        if isinstance(meta, dict):
            tokens["input_tokens"] = meta.get('prompt_token_count', 0) or meta.get('input_tokens', 0)
            tokens["output_tokens"] = meta.get('candidates_token_count', 0) or meta.get('output_tokens', 0)
            tokens["thinking_tokens"] = meta.get('thoughts_token_count', 0) or meta.get('total_thought_tokens', 0)
    
    tokens["total_tokens"] = (
        tokens["input_tokens"] + 
        tokens["output_tokens"] + 
        tokens["thinking_tokens"]
    )
    
    return tokens


def build_part(part: Dict) -> types.Part:
    """
    Build a Part object from a dict.
    
    Args:
        part: Dict with either 'text' or 'inline_data' key
        
    Returns:
        types.Part object
        
    Raises:
        ValueError: If part type is unknown
    """
    if "text" in part:
        return types.Part(text=part["text"])
    elif "inline_data" in part:
        return types.Part(
            inline_data=types.Blob(
                mime_type=part["inline_data"]["mime_type"],
                data=part["inline_data"]["data"],
            )
        )
    else:
        raise ValueError(f"Unknown part type: {part}")


def extract_thinking_from_response(response) -> str:
    """
    Extract thinking/reasoning text from Gemini response.
    
    Args:
        response: Gemini API response
        
    Returns:
        Accumulated thinking text
    """
    thinking_text = ""
    if hasattr(response, 'candidates') and response.candidates:
        for candidate in response.candidates:
            if hasattr(candidate, 'content') and candidate.content:
                for part in candidate.content.parts:
                    if hasattr(part, 'thought') and part.thought:
                        thinking_text += str(part.thought)
    return thinking_text


def extract_text_from_response(response) -> str:
    """
    Extract text content from Gemini response.
    
    Args:
        response: Gemini API response
        
    Returns:
        Response text
    """
    if hasattr(response, 'text'):
        return response.text
    return ""
