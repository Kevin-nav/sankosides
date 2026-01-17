"""
SankoSlides Export Module

Handles export of generated presentations to PowerPoint (.pptx) and PDF formats.
Key features:
- Fully editable equations in PowerPoint via LaTeX → OMML conversion
- High-fidelity PDF rendering via Playwright
- Theme support with customizable PowerPoint templates
- R2 cloud storage with signed URLs
"""

from app.export.router import router

__all__ = ["router"]
