"""
Synthesis Tool for CrewAI

Purpose: Convert PDF documents into a structured KnowledgeBase
using Gemini 3 Flash multimodal capabilities.

IMPORTANT: This tool extracts EXACT, VERBATIM content from PDFs.
The content is NOT summarized - it preserves original text for
accurate citations and references in generated slides.

v8.0: Now uses optimized GeminiExtractionService for 95% cost reduction.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from app.models.schemas import KnowledgeBase
from app.core.logging import get_logger

logger = get_logger(__name__)


class SynthesisError(Exception):
    """Exception raised when PDF synthesis fails."""
    pass


class SynthesisToolInput(BaseModel):
    """Input for the SynthesisTool."""
    file_path: str = Field(description="The path to the PDF file to be synthesized.")


class SynthesisTool(BaseTool):
    """
    Processes a PDF file, extracting its EXACT structure, text, and visual elements 
    into a structured KnowledgeBase.
    
    Content is extracted VERBATIM (not summarized) to support accurate academic citations.
    
    v8.0: Uses optimized extraction with:
    - Local PDF chunking (97% fewer input tokens)
    - Batch API (50% discount)
    - JSON repair (handles truncated responses)
    - Parallel sync retry (guarantees completion)
    """
    name: str = "PDF Synthesizer"
    description: str = (
        "Processes a PDF file, extracting its EXACT structure, text, and visual elements "
        "into a structured KnowledgeBase. Content is verbatim for citation accuracy."
    )
    args_schema: type[BaseModel] = SynthesisToolInput

    def _run(self, file_path: str) -> KnowledgeBase:
        """
        Execute the PDF synthesis using v8 optimized extraction.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            KnowledgeBase with extracted content
            
        Raises:
            SynthesisError: If synthesis fails
        """
        from app.services.gemini_extraction import GeminiExtractionService
        
        # Validate file exists
        pdf_path = Path(file_path)
        if not pdf_path.exists():
            raise SynthesisError(f"File not found at {file_path}")
        
        try:
            # Use optimized v8 extraction service
            service = GeminiExtractionService()
            knowledge_base = service.extract_from_pdf(pdf_path)
            
            logger.info(
                f"Successfully synthesized {file_path}: "
                f"{len(knowledge_base.sections)} sections extracted"
            )
            return knowledge_base
            
        except ValueError as e:
            # API key not configured
            raise SynthesisError(str(e))
        except Exception as e:
            logger.error(f"Synthesis failed for {file_path}: {e}")
            raise SynthesisError(f"Synthesis failed: {e}")

