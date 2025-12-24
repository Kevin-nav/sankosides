"""
Pipeline Module - Modular Slide Generation Pipeline

This module contains the modularized slide generation pipeline,
broken down from the monolithic crew.py file.

Exports:
    - SlideGenerationPipeline: Main orchestrator
    - PipelineResult, SlideResult: Result models
    - Individual stages for testing
"""

from app.pipeline.base import SlideResult, PipelineResult
from app.pipeline.orchestrator import SlideGenerationPipeline, generate_slides, get_available_themes

__all__ = [
    "SlideGenerationPipeline",
    "generate_slides",
    "get_available_themes",
    "PipelineResult",
    "SlideResult",
]
