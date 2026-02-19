"""
SankoSlides Export Module

Handles export of generated presentations to PowerPoint (.pptx) and PDF formats.
Key features:
- Fully editable equations in PowerPoint via LaTeX → OMML conversion
- High-fidelity PDF rendering via Playwright
- Theme support with customizable PowerPoint templates
- R2 cloud storage with signed URLs
"""

try:
    from app.export.router import router
except ModuleNotFoundError:
    # Allows utility-level imports (e.g., exporter unit tests) without API deps.
    router = None

__all__ = ["router"]
