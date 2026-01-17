"""
Export API Router

Endpoints for exporting presentations to PowerPoint and PDF formats.
"""

from typing import List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import datetime

from app.export.models import (
    ExportFormat,
    ExportRequest,
    ExportResponse,
    ExportOptions,
    ExportStatus,
    ExportJobStatus,
)
from app.export.pptx_exporter import export_to_pptx, export_to_pptx_async
from app.export.pdf_exporter import export_to_pdf
from app.export.storage import upload_export
from app.models.schemas import RefinedSlide, SlideContentType
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/export", tags=["export"])


# ============================================================================
# Test/Demo Data (for development)
# ============================================================================

def _get_demo_slides() -> List[RefinedSlide]:
    """Generate demo slides for testing exports."""
    return [
        RefinedSlide(
            order=1,
            title="Introduction to Quantum Mechanics",
            content_type=SlideContentType.TITLE,
            bullet_points=["Physics 301 - Spring 2025"],
        ),
        RefinedSlide(
            order=2,
            title="The Schrödinger Equation",
            content_type=SlideContentType.EQUATION,
            bullet_points=[
                "Describes the wave function evolution",
                "Fundamental to quantum mechanics",
            ],
            equation_latex=r"i\hbar\frac{\partial}{\partial t}\Psi = \hat{H}\Psi",
        ),
        RefinedSlide(
            order=3,
            title="Quantum State Evolution",
            content_type=SlideContentType.DIAGRAM,
            bullet_points=[
                "States evolve according to Schrödinger equation",
            ],
            diagram_svg=None,  # SVG would be rendered here
            diagram_mermaid="""flowchart LR
    A[Initial State ψ₀] --> B[Time Evolution]
    B --> C[Final State ψₜ]
    B --> D[Measurement]
    D --> E[Collapse to Eigenstate]""",
        ),
        RefinedSlide(
            order=4,
            title="Wave-Particle Duality",
            content_type=SlideContentType.CONTENT,
            bullet_points=[
                "Light exhibits both wave and particle properties",
                "de Broglie wavelength: λ = h/p",
                "Confirmed by double-slit experiment",
                "Foundation of quantum theory",
            ],
        ),
        RefinedSlide(
            order=5,
            title="Key Takeaways",
            content_type=SlideContentType.CONCLUSION,
            bullet_points=[
                "Quantum mechanics describes nature at atomic scales",
                "Wave functions contain all measurable information",
                "Measurement causes wave function collapse",
            ],
        ),
    ]


# ============================================================================
# Export Endpoints
# ============================================================================

@router.post("/{format}", response_model=ExportResponse)
async def export_presentation(
    format: ExportFormat,
    request: ExportRequest,
    background_tasks: BackgroundTasks,
):
    """
    Export a presentation to PowerPoint or PDF format.
    
    Supports:
    - **pptx**: PowerPoint with editable equations (OMML) and diagrams
    - **pdf**: High-fidelity PDF with MathJax equations
    
    Returns a signed download URL valid for 1 hour.
    """
    logger.info(f"Export requested: format={format}, presentation_id={request.presentation_id}")
    
    try:
        # TODO: Fetch actual slides from database using presentation_id
        # For now, using demo slides for testing
        if request.presentation_id == "demo":
            slides = _get_demo_slides()
            title = "Quantum Mechanics Introduction"
        else:
            # In production, fetch from database
            raise HTTPException(
                status_code=404,
                detail=f"Presentation not found: {request.presentation_id}. Use 'demo' for testing."
            )
        
        # Export based on format
        if format == ExportFormat.PDF:
            # PDF export via render service
            logger.info("Generating PDF export")
            export_bytes = await export_to_pdf(
                slides=slides,
                title=title,
                format=request.options.pdf_format,
                include_notes=request.options.include_notes,
            )
        else:
            # PPTX export
            has_diagrams = any(s.diagram_svg or s.diagram_mermaid for s in slides)
            
            if has_diagrams:
                logger.info("Using async export for diagram rendering")
                export_bytes = await export_to_pptx_async(
                    slides=slides,
                    title=title,
                    theme_id=request.theme_id,
                    editable_equations=request.options.editable_equations,
                    image_dpi=request.options.image_dpi,
                )
            else:
                export_bytes = export_to_pptx(
                    slides=slides,
                    title=title,
                    theme_id=request.theme_id,
                    editable_equations=request.options.editable_equations,
                    image_dpi=request.options.image_dpi,
                )
        
        # Upload to R2 and get download URL
        download_url, filename, expires_at, file_size = await upload_export(
            file_data=export_bytes,
            format=format,
            presentation_title=title,
        )
        
        logger.info(f"Export complete: {filename} ({file_size} bytes)")
        
        return ExportResponse(
            download_url=download_url,
            expires_at=expires_at,
            file_size_bytes=file_size,
            format=format,
            filename=filename,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Export failed: {str(e)}"
        )


@router.post("/demo/pptx", response_model=ExportResponse)
async def export_demo_presentation():
    """
    Export a demo presentation for testing.
    
    Generates a sample quantum mechanics presentation to verify
    the export pipeline is working correctly.
    """
    return await export_presentation(
        format=ExportFormat.PPTX,
        request=ExportRequest(
            presentation_id="demo",
            theme_id="academic",
            options=ExportOptions(),
        ),
        background_tasks=BackgroundTasks(),
    )


@router.get("/formats")
async def list_export_formats():
    """List available export formats and their capabilities."""
    return {
        "formats": [
            {
                "id": "pptx",
                "name": "PowerPoint",
                "extension": ".pptx",
                "available": True,
                "features": [
                    "Editable equations (OMML)",
                    "Theme support",
                    "High-res diagrams",
                ],
            },
            {
                "id": "pdf",
                "name": "PDF",
                "extension": ".pdf",
                "available": True,
                "features": [
                    "Print-ready quality",
                    "MathJax equations",
                    "Page formats: 16:9, 4:3, A4, Letter",
                ],
            },
        ]
    }
