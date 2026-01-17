"""
Export API Models

Pydantic models for export request/response handling.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class ExportFormat(str, Enum):
    """Supported export formats."""
    PPTX = "pptx"
    PDF = "pdf"


class ExportOptions(BaseModel):
    """Configuration options for export."""
    
    # Quality settings
    image_dpi: int = Field(
        default=300,
        ge=72,
        le=600,
        description="DPI for embedded diagrams and images"
    )
    
    # Equation handling
    equation_fallback: Literal["svg", "png"] = Field(
        default="svg",
        description="Fallback format if OMML conversion fails"
    )
    
    # PDF-specific options
    pdf_format: Literal["16:9", "4:3", "A4", "Letter"] = Field(
        default="16:9",
        description="PDF page format/aspect ratio"
    )
    include_notes: bool = Field(
        default=False,
        description="Include speaker notes in PDF"
    )
    
    # PPT-specific options
    editable_equations: bool = Field(
        default=True,
        description="Convert LaTeX to editable OMML equations"
    )


class ExportRequest(BaseModel):
    """Request to export a presentation."""
    
    presentation_id: str = Field(
        ...,
        description="ID of the generated presentation to export"
    )
    theme_id: str = Field(
        default="academic",
        description="Theme to apply to the export"
    )
    options: ExportOptions = Field(
        default_factory=ExportOptions,
        description="Export configuration options"
    )


class ExportResponse(BaseModel):
    """Response from export endpoint."""
    
    download_url: str = Field(
        ...,
        description="Signed R2 URL to download the exported file"
    )
    expires_at: datetime = Field(
        ...,
        description="When the download URL expires"
    )
    file_size_bytes: int = Field(
        ...,
        ge=0,
        description="Size of the exported file"
    )
    format: ExportFormat = Field(
        ...,
        description="Format of the exported file"
    )
    filename: str = Field(
        ...,
        description="Suggested filename for download"
    )


class ExportStatus(str, Enum):
    """Status of an export job."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ExportJobStatus(BaseModel):
    """Status of an in-progress export job."""
    
    job_id: str
    status: ExportStatus
    progress_percent: int = Field(default=0, ge=0, le=100)
    message: Optional[str] = None
    result: Optional[ExportResponse] = None
    error: Optional[str] = None
