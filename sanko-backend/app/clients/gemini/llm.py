"""
CrewAI LLM Configuration for Google Gemini

Sets up Gemini API access for CrewAI agents using LiteLLM integration.
"""

import os
from crewai import LLM

from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# =============================================================================
# CRITICAL: Set API keys at module load time, BEFORE any LLM is instantiated
# =============================================================================

# CrewAI uses LiteLLM which looks for GOOGLE_API_KEY or GEMINI_API_KEY
if settings.gemini_api_key:
    os.environ["GOOGLE_API_KEY"] = settings.gemini_api_key
    os.environ["GEMINI_API_KEY"] = settings.gemini_api_key
    logger.info("Gemini API key configured from settings")
else:
    logger.warning("GEMINI_API_KEY not set - LLM calls will fail")


# =============================================================================
# LLM Factory Functions
# =============================================================================

def get_flash_llm(temperature: float = 0.7) -> LLM:
    """
    Get a Gemini Flash model for fast, routine tasks.
    
    Uses gemini-2.0-flash - the latest fast model.
    """
    return LLM(
        model="gemini/gemini-2.0-flash",
        temperature=temperature,
    )


def get_pro_llm(temperature: float = 0.7) -> LLM:
    """
    Get a Gemini Pro model for complex reasoning tasks.
    
    Uses gemini-2.0-flash-thinking-exp for deep reasoning.
    """
    return LLM(
        model="gemini/gemini-2.0-flash-thinking-exp",
        temperature=temperature,
    )


# =============================================================================
# Convenience Aliases Matching Agent Roles
# =============================================================================

# Fast agents use Flash
CLARIFIER_LLM = lambda: get_flash_llm(0.7)      # Fast Q&A
OUTLINER_LLM = lambda: get_flash_llm(0.5)       # Document parsing
GENERATOR_LLM = lambda: get_flash_llm(0.6)      # HTML generation
VISUAL_QA_LLM = lambda: get_flash_llm(0.5)      # Vision grading

# Complex reasoning agents use Pro/Thinking
PLANNER_LLM = lambda: get_pro_llm(0.7)          # Deep content planning
REFINER_LLM = lambda: get_pro_llm(0.6)          # Quality verification
HELPER_LLM = lambda: get_pro_llm(0.7)           # Complex fixing


# =============================================================================
# Legacy Compatibility - GeminiLLM class for existing code
# =============================================================================

class GeminiLLM:
    """
    Legacy wrapper for backward compatibility.
    
    Creates a standard CrewAI LLM with Gemini configuration.
    """
    
    def __new__(
        cls,
        model: str = "gemini-2.0-flash",
        thinking_level: str = "medium",
        **kwargs
    ) -> LLM:
        """Return a configured LLM instance instead of GeminiLLM."""
        # Map thinking level to temperature
        temp_map = {
            "minimal": 0.3,
            "low": 0.5,
            "medium": 0.7,
            "high": 0.9,
        }
        temperature = temp_map.get(thinking_level, 0.7)
        
        # Normalize model name
        if not model.startswith("gemini/"):
            model = f"gemini/{model}"
        
        return LLM(
            model=model,
            temperature=temperature,
        )
