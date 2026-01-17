"""
Configuration for Gemini PDF synthesis testing.
Loads API key and settings from environment variables.
"""

import os
from pathlib import Path
from typing import Optional

# Try to load from .env file if python-dotenv is available
try:
    from dotenv import load_dotenv
    
    # Load from local .env first, then fall back to sanko-backend .env
    local_env = Path(__file__).parent / ".env"
    backend_env = Path(__file__).parent.parent.parent / "sanko-backend" / ".env"
    
    if local_env.exists():
        load_dotenv(local_env)
    elif backend_env.exists():
        load_dotenv(backend_env)
except ImportError:
    pass


# ============================================
# Gemini API Configuration
# ============================================

def get_api_key() -> str:
    """
    Get Gemini API key from environment.
    
    Priority:
    1. GEMINI_API_KEY environment variable
    2. GOOGLE_API_KEY environment variable (fallback)
    """
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    
    if not api_key:
        raise ValueError(
            "Gemini API key not found!\n\n"
            "Set one of these environment variables:\n"
            "  - GEMINI_API_KEY=your_key_here\n"
            "  - GOOGLE_API_KEY=your_key_here\n\n"
            "Or create a .env file in:\n"
            f"  - {Path(__file__).parent}\n"
            f"  - {Path(__file__).parent.parent.parent / 'sanko-backend'}\n\n"
            "Get your API key at: https://aistudio.google.com/apikey"
        )
    
    return api_key


# Available Gemini 3 models (as of December 2025)
# See: https://ai.google.dev/gemini-api/docs/models
GEMINI_MODELS = {
    # Gemini 3 (latest)
    "gemini-3-flash-preview": "Fast, frontier-class performance (default)",
    "gemini-3-pro-preview": "Complex agentic problems, strong coding/reasoning",
    
    # Gemini 2.5 (previous gen)
    "gemini-2.5-flash": "Previous generation Flash",
    "gemini-2.5-pro": "Previous generation Pro",
}

# Default model for synthesis
DEFAULT_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")


# ============================================
# Test Configuration
# ============================================

# Default directory containing test PDFs
DEFAULT_PDF_DIR = Path(__file__).parent.parent.parent / "pdfs_for_testing"

# Default number of runs per strategy
DEFAULT_RUNS_PER_STRATEGY = int(os.environ.get("TEST_RUNS_PER_STRATEGY", "3"))

# Results output directory
RESULTS_DIR = Path(__file__).parent / "results"


# ============================================
# Display Configuration
# ============================================

def print_config_summary():
    """Print current configuration for visibility."""
    print()
    print("=" * 60)
    print("CONFIGURATION SUMMARY")
    print("=" * 60)
    
    # API Key status
    try:
        key = get_api_key()
        masked_key = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
        print(f"API Key:       {masked_key}")
    except ValueError:
        print("API Key:       NOT SET")
    
    print(f"Default Model: {DEFAULT_MODEL}")
    print(f"PDF Dir:       {DEFAULT_PDF_DIR}")
    print(f"Results Dir:   {RESULTS_DIR}")
    print(f"Runs/Strategy: {DEFAULT_RUNS_PER_STRATEGY}")
    print("=" * 60)
    print()


if __name__ == "__main__":
    # Test configuration when run directly
    print_config_summary()
    
    print("Available models:")
    for model, desc in GEMINI_MODELS.items():
        marker = " ->" if model == DEFAULT_MODEL else "   "
        print(f"  {marker} {model}: {desc}")
