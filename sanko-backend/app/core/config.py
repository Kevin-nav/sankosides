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
    port: int = 8000
    debug: bool = True
    
    # Render Service
    render_service_url: str = "http://localhost:3001"
    
    # Optional Firebase (for JWT verification)
    firebase_project_id: Optional[str] = None
    
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
