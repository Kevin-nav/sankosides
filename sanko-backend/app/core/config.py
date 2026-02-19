"""
SankoSlides Backend Configuration

Loads environment variables and provides typed configuration settings.
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Google Gemini API
    gemini_api_key: str = ""
    
    # Database
    database_url: str = ""
    
    # CORS
    frontend_url: str = "http://localhost:3000"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8080
    debug: bool = True
    
    # Render Service
    render_service_url: str = "http://localhost:3001"
    
    # Cloudflare R2 Storage
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = "duotrak"
    r2_public_url: Optional[str] = None  # Optional: Custom domain for public access
    
    # Upstash Redis (for caching)
    redis_url: Optional[str] = None  # Upstash Redis URL (rediss://...)
    
    # Optional Firebase (for JWT verification)
    firebase_project_id: Optional[str] = None

    # Feature Flags
    enable_convex_cache: bool = False
    require_evidence_for_claims: bool = False
    enable_gemini_explicit_cache: bool = False
    enable_element_tree_pipeline: bool = False
    enable_element_tree_canvas: bool = False
    enable_element_tree_export: bool = False
    gemini_cache_ttl_seconds: int = 900
    extraction_min_sections: int = 3
    extraction_min_coverage_ratio: float = 0.6
    
    # Academic Search APIs
    semantic_scholar_api_key: Optional[str] = None  # Get from semanticscholar.org/product/api
    
    # Gemini 3 Model Names (December 2025)
    model_flash: str = "gemini-3-flash-preview"  # Fast, multimodal, native PDF support
    model_pro: str = "gemini-3-pro-preview"  # Deep reasoning, agentic workflows
    model_image: str = "gemini-3-pro-image-preview"  # Nano Banana Pro for asset generation
    
    # Thinking Level Configuration (Gemini 3 feature)
    thinking_level_low: str = "low"  # Speed-optimized (quick interactions)
    thinking_level_medium: str = "medium"  # Balanced (document parsing, outlining)
    thinking_level_high: str = "high"  # Reasoning-optimized (verification, generation)
    
    # Slide Dimensions - Exact PowerPoint 16:9 Standard (1280x720 @ 96 DPI)
    # This matches PowerPoint's default "Widescreen (16:9)" setting
    SLIDE_WIDTH: int = 1280
    SLIDE_HEIGHT: int = 720
    SLIDE_DPI: int = 96
    
    # Development Mode Settings
    # Set to False in production to hide internal metrics
    dev_mode: bool = True  # Toggle via DEV_MODE env var
    expose_metrics: bool = True  # Toggle via EXPOSE_METRICS env var
    
    # Agent Execution Timeouts (seconds)
    # These control how long to wait for AI agents before timing out
    agent_timeout_outliner: int = 170  # Outliner agent timeout
    agent_timeout_planner: int = 200   # Planner agent timeout
    agent_timeout_refiner: int = 200   # Refiner agent timeout
    agent_timeout_generator: int = 140  # Generator agent timeout
    agent_timeout_visual_qa: int = 140  # Visual QA agent timeout
    agent_max_retries: int = 3         # Max retries for agent execution
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Slide dimension constants for easy import
SLIDE_WIDTH = 1280
SLIDE_HEIGHT = 720
SLIDE_DPI = 96


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Dependency injection for settings."""
    return settings
