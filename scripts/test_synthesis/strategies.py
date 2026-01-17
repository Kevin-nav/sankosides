"""
Synthesis strategies for testing different approaches.
"""

import os
import sys
import json
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

# Add the backend to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sanko-backend"))

from google import genai
from google.genai import types

from metrics import (
    SynthesisRunMetrics, 
    MetricsTimer, 
    ErrorType,
    detect_truncation,
    analyze_latex_content,
    repair_truncated_json,
)


# Available Gemini models (verified Dec 2025)
GEMINI_MODELS = {
    "gemini-3-flash-preview": "Fast, frontier-class performance",
    "gemini-3-pro-preview": "Complex agentic problems, strong coding/reasoning",
    "gemini-2.5-flash": "Previous generation Flash",
    "gemini-2.5-pro": "Previous generation Pro",
}


# Base prompt for synthesis
BASE_SYNTHESIS_PROMPT = """
You are a specialized STEM content extractor. Your goal is to convert the provided PDF into a structured JSON object representing a KnowledgeBase.

CRITICAL: Extract the EXACT, VERBATIM text from each section. Do NOT summarize or paraphrase.
The extracted content will be used for academic citations and must match the original document precisely.

FOLLOW THESE STRICT RULES:
1.  **JSON Output:** Your entire output MUST be a single, valid JSON object.
2.  **Schema:** The JSON object must conform to this Pydantic schema:
    ```json
    {
      "summary": "High-level overview of the entire document set.",
      "sections": [
        {
          "title": "Section header or topic",
          "content": "EXACT, VERBATIM text and latex content for this section - DO NOT SUMMARIZE.",
          "visuals": ["Description of any diagrams, charts, etc."],
          "page_range": "e.g., '1-3'"
        }
      ]
    }
    ```
3.  **Verbatim Extraction:** Copy text EXACTLY as it appears. Preserve all details.
4.  **Equations:** Extract ALL mathematical formulas as valid LaTeX within the 'content' field. Use $...$ for inline and $$...$$ for block equations.
5.  **Visuals:** Identify every diagram, chart, or image and add a detailed description to the 'visuals' list for that section.
6.  **Page Ranges:** ALWAYS include the page_range for each section (e.g., "1-2", "3", "4-6").
7.  **Hierarchy:** Use the document's structure to create logical sections.

Output ONLY the JSON object. Do not include any other text or formatting.
"""


@dataclass
class SynthesisResult:
    """Result of a synthesis operation."""
    success: bool
    knowledge_base: Optional[Dict[str, Any]] = None
    raw_response: str = ""
    error_message: Optional[str] = None
    error_type: ErrorType = ErrorType.SUCCESS


class SynthesisStrategy(ABC):
    """Base class for synthesis strategies."""
    
    name: str = "base"
    description: str = "Base strategy"
    
    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview"):
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(api_key=api_key)
    
    @abstractmethod
    def synthesize(self, pdf_path: Path, metrics: SynthesisRunMetrics) -> SynthesisResult:
        """Execute the synthesis strategy."""
        pass
    
    def _call_gemini(
        self, 
        pdf_data: bytes, 
        prompt: str, 
        temperature: float = 0.0
    ) -> Tuple[str, float]:
        """
        Make a Gemini API call and return response text and latency.
        """
        with MetricsTimer() as timer:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=pdf_data, mime_type="application/pdf"),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    temperature=temperature,
                    response_mime_type="application/json",
                )
            )
        return response.text, timer.elapsed_ms
    
    def _parse_json(self, text: str, try_repair: bool = True) -> Tuple[Optional[Dict], Optional[str], bool]:
        """
        Parse JSON response with optional repair.
        
        Returns:
            (data, error_message, was_repaired)
        """
        try:
            return json.loads(text), None, False
        except json.JSONDecodeError as e:
            if not try_repair:
                return None, str(e), False
            
            # Try to repair truncated/malformed JSON
            repaired, was_repaired, repair_notes = repair_truncated_json(text)
            if repaired:
                return repaired, f"repaired:{repair_notes}", True
            return None, str(e), False
    
    def _update_quality_metrics(self, metrics: SynthesisRunMetrics, kb: Dict[str, Any]):
        """Update quality metrics from a parsed knowledge base."""
        sections = kb.get("sections", [])
        
        # Handle case where sections might not be a list
        if not isinstance(sections, list):
            sections = []
        
        metrics.quality.sections_count = len(sections)
        
        content_lengths = []
        for section in sections:
            # Skip if section is not a dict (Gemini sometimes returns malformed data)
            if not isinstance(section, dict):
                continue
                
            content = section.get("content", "")
            if not isinstance(content, str):
                content = str(content) if content else ""
            
            content_len = len(content)
            content_lengths.append(content_len)
            
            if content_len == 0:
                metrics.quality.empty_sections += 1
            if section.get("visuals"):
                metrics.quality.sections_with_visuals += 1
            if section.get("page_range"):
                metrics.quality.sections_with_page_range += 1
            if analyze_latex_content(content):
                metrics.quality.sections_with_latex += 1
        
        if content_lengths:
            metrics.quality.total_content_chars = sum(content_lengths)
            metrics.quality.avg_section_chars = sum(content_lengths) / len(content_lengths)
            metrics.quality.min_section_chars = min(content_lengths)
            metrics.quality.max_section_chars = max(content_lengths)


class BaselineStrategy(SynthesisStrategy):
    """
    Current baseline: Single prompt, full PDF.
    """
    name = "baseline"
    description = "Single prompt with full PDF, default settings"
    
    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview", temperature: float = 0.0):
        super().__init__(api_key, model)
        self.temperature = temperature
    
    def synthesize(self, pdf_path: Path, metrics: SynthesisRunMetrics) -> SynthesisResult:
        metrics.strategy_params = {
            "model": self.model,
            "temperature": self.temperature,
        }
        
        # Read PDF
        try:
            pdf_data = pdf_path.read_bytes()
        except IOError as e:
            return SynthesisResult(
                success=False,
                error_message=str(e),
                error_type=ErrorType.FILE_ERROR,
            )
        
        # Call Gemini
        try:
            with MetricsTimer() as total_timer:
                raw_response, api_latency = self._call_gemini(
                    pdf_data, BASE_SYNTHESIS_PROMPT, self.temperature
                )
                metrics.performance.api_latency_ms = api_latency
                
                # Record response metrics
                metrics.response.raw_response_chars = len(raw_response)
                metrics.response.response_tokens_estimate = len(raw_response) // 4
                
                # Check for truncation
                is_truncated, indicators = detect_truncation(raw_response)
                metrics.response.appears_truncated = is_truncated
                metrics.response.truncation_indicators = indicators
                
                # Parse JSON (with repair attempt for truncated responses)
                with MetricsTimer() as parse_timer:
                    kb, parse_error, was_repaired = self._parse_json(raw_response)
                metrics.performance.json_parse_time_ms = parse_timer.elapsed_ms
                
                if kb is None:
                    # Parse failed even after repair attempt
                    metrics.response.valid_json = False
                    metrics.response.json_parse_error = parse_error
                    metrics.failure.success = False
                    metrics.failure.error_type = ErrorType.JSON_TRUNCATED if is_truncated else ErrorType.JSON_PARSE_ERROR
                    metrics.failure.error_message = parse_error
                    metrics.failure.failed_at_stage = "json_parse"
                    return SynthesisResult(
                        success=False,
                        raw_response=raw_response,
                        error_message=parse_error,
                        error_type=metrics.failure.error_type,
                    )
                
                # Mark as valid (possibly repaired)
                metrics.response.valid_json = True
                if was_repaired:
                    metrics.response.json_parse_error = parse_error  # Contains repair notes
                
                # Validate and update quality metrics
                with MetricsTimer() as validate_timer:
                    self._update_quality_metrics(metrics, kb)
                metrics.performance.validation_time_ms = validate_timer.elapsed_ms
            
            metrics.performance.total_time_ms = total_timer.elapsed_ms
            metrics.failure.success = True
            
            return SynthesisResult(
                success=True,
                knowledge_base=kb,
                raw_response=raw_response,
            )
            
        except Exception as e:
            metrics.failure.success = False
            metrics.failure.error_type = ErrorType.API_ERROR
            metrics.failure.error_message = str(e)
            metrics.failure.failed_at_stage = "api_call"
            return SynthesisResult(
                success=False,
                error_message=str(e),
                error_type=ErrorType.API_ERROR,
            )


class TemperatureVariationStrategy(BaselineStrategy):
    """Test different temperature values."""
    name = "temperature_variation"
    description = "Baseline with different temperature settings"
    
    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview", temperature: float = 0.1):
        super().__init__(api_key, model, temperature)


class ModelComparisonStrategy(BaselineStrategy):
    """Test different Gemini models."""
    name = "model_comparison"
    description = "Compare different Gemini models"


class ChunkedStrategy(SynthesisStrategy):
    """
    Split PDF into page chunks, synthesize each, then merge.
    Handles sections that may span chunk boundaries.
    """
    name = "chunked"
    description = "Process PDF in page-range chunks with boundary handling"
    
    def __init__(
        self, 
        api_key: str, 
        model: str = "gemini-3-flash-preview",
        pages_per_chunk: int = 10,
        overlap_pages: int = 2,  # Overlap to catch cross-boundary sections
    ):
        super().__init__(api_key, model)
        self.pages_per_chunk = pages_per_chunk
        self.overlap_pages = overlap_pages
    
    def synthesize(self, pdf_path: Path, metrics: SynthesisRunMetrics) -> SynthesisResult:
        metrics.strategy_params = {
            "model": self.model,
            "pages_per_chunk": self.pages_per_chunk,
            "overlap_pages": self.overlap_pages,
        }
        
        try:
            import fitz  # PyMuPDF
        except ImportError:
            return SynthesisResult(
                success=False,
                error_message="PyMuPDF (fitz) not installed. Run: pip install PyMuPDF",
                error_type=ErrorType.UNKNOWN,
            )
        
        # Open PDF and get page count
        try:
            doc = fitz.open(pdf_path)
            total_pages = len(doc)
        except Exception as e:
            return SynthesisResult(
                success=False,
                error_message=f"Failed to open PDF: {e}",
                error_type=ErrorType.FILE_ERROR,
            )
        
        # Calculate chunks with overlap
        chunks = []
        start = 0
        while start < total_pages:
            end = min(start + self.pages_per_chunk, total_pages)
            chunks.append((start, end))
            start = end - self.overlap_pages if end < total_pages else end
        
        metrics.chunks_processed = len(chunks)
        all_sections = []
        chunk_responses = []
        
        with MetricsTimer() as total_timer:
            for chunk_idx, (start_page, end_page) in enumerate(chunks):
                # Extract chunk to temp PDF
                try:
                    chunk_doc = fitz.open()
                    chunk_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
                    
                    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                        chunk_doc.save(tmp.name)
                        chunk_path = tmp.name
                    
                    chunk_data = Path(chunk_path).read_bytes()
                    chunk_doc.close()
                except Exception as e:
                    return SynthesisResult(
                        success=False,
                        error_message=f"Failed to extract chunk {chunk_idx}: {e}",
                        error_type=ErrorType.FILE_ERROR,
                    )
                
                # Create chunk-specific prompt
                chunk_prompt = f"""
{BASE_SYNTHESIS_PROMPT}

IMPORTANT: This is pages {start_page + 1} to {end_page} of a larger document.
- Adjust page_range values to be relative to the ORIGINAL document (add {start_page} to page numbers).
- If a section appears to continue from a previous page or continues to the next, note this in the title with "[continued]" or "[continues]".
"""
                
                # Call Gemini for this chunk
                try:
                    raw_response, api_latency = self._call_gemini(chunk_data, chunk_prompt)
                    metrics.performance.chunk_times_ms.append(api_latency)
                    
                    kb, parse_error, was_repaired = self._parse_json(raw_response)
                    if kb is None:
                        # Log but continue with other chunks
                        chunk_responses.append({
                            "chunk": chunk_idx,
                            "pages": f"{start_page + 1}-{end_page}",
                            "error": parse_error,
                        })
                        continue
                    
                    chunk_responses.append({
                        "chunk": chunk_idx,
                        "pages": f"{start_page + 1}-{end_page}",
                        "sections": len(kb.get("sections", []) if isinstance(kb.get("sections"), list) else []),
                        "repaired": was_repaired,
                    })
                    
                    sections = kb.get("sections", [])
                    if isinstance(sections, list):
                        all_sections.extend(sections)
                    
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(chunk_path)
                    except:
                        pass
            
            # Merge sections, handling overlaps
            merged_sections = self._merge_overlapping_sections(all_sections)
            metrics.quality.merged_sections = len(all_sections) - len(merged_sections)
            
            # Build final KB
            final_kb = {
                "summary": f"Extracted from {total_pages} pages in {len(chunks)} chunks",
                "sections": merged_sections,
            }
            
            self._update_quality_metrics(metrics, final_kb)
        
        doc.close()
        metrics.performance.total_time_ms = total_timer.elapsed_ms
        metrics.performance.api_latency_ms = sum(metrics.performance.chunk_times_ms)
        metrics.failure.success = True
        
        return SynthesisResult(
            success=True,
            knowledge_base=final_kb,
            raw_response=json.dumps(chunk_responses),
        )
    
    def _merge_overlapping_sections(self, sections: List[Dict]) -> List[Dict]:
        """
        Merge sections that appear to be from overlapping chunks.
        Uses title similarity and page range analysis.
        """
        if not sections:
            return []
        
        merged = []
        skip_indices = set()
        
        for i, section in enumerate(sections):
            if i in skip_indices:
                continue
            
            current = section.copy()
            title = current.get("title", "").lower()
            
            # Look for continuation sections
            for j in range(i + 1, len(sections)):
                if j in skip_indices:
                    continue
                
                other = sections[j]
                other_title = other.get("title", "").lower()
                
                # Check for continuation markers
                is_continuation = (
                    "[continued]" in other_title or
                    "[continues]" in title or
                    self._titles_match(title, other_title)
                )
                
                if is_continuation:
                    # Merge content
                    current["content"] = current.get("content", "") + "\n\n" + other.get("content", "")
                    # Merge visuals
                    current["visuals"] = current.get("visuals", []) + other.get("visuals", [])
                    # Update page range
                    current["page_range"] = self._merge_page_ranges(
                        current.get("page_range", ""),
                        other.get("page_range", "")
                    )
                    skip_indices.add(j)
            
            # Clean up title
            current["title"] = current["title"].replace("[continued]", "").replace("[continues]", "").strip()
            merged.append(current)
        
        return merged
    
    def _titles_match(self, title1: str, title2: str) -> bool:
        """Check if two titles refer to the same section."""
        # Remove common variations
        clean1 = title1.replace("[continued]", "").replace("[continues]", "").strip()
        clean2 = title2.replace("[continued]", "").replace("[continues]", "").strip()
        return clean1 == clean2
    
    def _merge_page_ranges(self, range1: str, range2: str) -> str:
        """Merge two page range strings."""
        if not range1:
            return range2
        if not range2:
            return range1
        
        # Try to create a continuous range
        try:
            # Parse first pages
            parts1 = range1.split("-")
            parts2 = range2.split("-")
            start = int(parts1[0])
            end = int(parts2[-1]) if len(parts2) > 1 else int(parts2[0])
            return f"{start}-{end}"
        except:
            return f"{range1}, {range2}"


class TwoPhaseStrategy(SynthesisStrategy):
    """
    Two-phase extraction:
    1. First pass: Extract document structure/TOC only
    2. Second pass: Extract full content for each section
    """
    name = "two_phase"
    description = "First extract structure, then content per section"
    
    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview"):
        super().__init__(api_key, model)
    
    def synthesize(self, pdf_path: Path, metrics: SynthesisRunMetrics) -> SynthesisResult:
        metrics.strategy_params = {"model": self.model, "phases": 2}
        
        try:
            pdf_data = pdf_path.read_bytes()
        except IOError as e:
            return SynthesisResult(
                success=False,
                error_message=str(e),
                error_type=ErrorType.FILE_ERROR,
            )
        
        # Phase 1: Extract structure
        structure_prompt = """
You are extracting the TABLE OF CONTENTS / STRUCTURE from this PDF.

Output a JSON object with this schema:
{
  "document_title": "Title of the document",
  "sections": [
    {
      "title": "Section title exactly as it appears",
      "page_range": "e.g., '1-3'",
      "subsections": ["list of subsection titles if any"]
    }
  ]
}

Focus ONLY on identifying section boundaries and page ranges. Do not extract content yet.
"""
        
        with MetricsTimer() as total_timer:
            try:
                # Phase 1
                structure_response, phase1_latency = self._call_gemini(pdf_data, structure_prompt)
                metrics.performance.chunk_times_ms.append(phase1_latency)
                
                structure, parse_error, _ = self._parse_json(structure_response)
                if structure is None:
                    metrics.failure.success = False
                    metrics.failure.error_type = ErrorType.JSON_PARSE_ERROR
                    metrics.failure.error_message = f"Phase 1 parse error: {parse_error}"
                    return SynthesisResult(
                        success=False,
                        error_message=parse_error,
                        error_type=ErrorType.JSON_PARSE_ERROR,
                    )
                
                sections = structure.get("sections", [])
                if not isinstance(sections, list):
                    sections = []
                metrics.chunks_processed = len(sections) + 1  # +1 for structure phase
                
                # Phase 2: Extract content for each section
                all_sections = []
                for section_info in sections:
                    content_prompt = f"""
Extract the COMPLETE, VERBATIM content for this specific section:

Section: {section_info.get('title')}
Pages: {section_info.get('page_range', 'unknown')}

Output JSON:
{{
  "title": "{section_info.get('title')}",
  "content": "EXACT, VERBATIM text - DO NOT SUMMARIZE",
  "visuals": ["descriptions of diagrams/charts"],
  "page_range": "{section_info.get('page_range', '')}"
}}

Extract ONLY this section. Be thorough and include all LaTeX equations.
"""
                    
                    content_response, phase2_latency = self._call_gemini(pdf_data, content_prompt)
                    metrics.performance.chunk_times_ms.append(phase2_latency)
                    
                    section_data, _, _ = self._parse_json(content_response)
                    if section_data and isinstance(section_data, dict):
                        all_sections.append(section_data)
                
                # Build final KB
                final_kb = {
                    "summary": structure.get("document_title", "Extracted document"),
                    "sections": all_sections,
                }
                
                self._update_quality_metrics(metrics, final_kb)
                
            except Exception as e:
                metrics.failure.success = False
                metrics.failure.error_type = ErrorType.API_ERROR
                metrics.failure.error_message = str(e)
                return SynthesisResult(
                    success=False,
                    error_message=str(e),
                    error_type=ErrorType.API_ERROR,
                )
        
        metrics.performance.total_time_ms = total_timer.elapsed_ms
        metrics.performance.api_latency_ms = sum(metrics.performance.chunk_times_ms)
        metrics.failure.success = True
        
        return SynthesisResult(
            success=True,
            knowledge_base=final_kb,
        )


# Strategy registry
# Model names verified as of Dec 2025:
#   - gemini-3-flash-preview: Fast, frontier-class performance
#   - gemini-3-pro-preview: Complex agentic problems, strong coding/reasoning
STRATEGIES = {
    # Baseline with Gemini 3 Flash (latest)
    "baseline": BaselineStrategy,  # Uses gemini-3-flash-preview by default
    "baseline_t01": lambda api_key: TemperatureVariationStrategy(api_key, temperature=0.1),
    "baseline_t02": lambda api_key: TemperatureVariationStrategy(api_key, temperature=0.2),
    # Chunked strategies
    "chunked_10": lambda api_key: ChunkedStrategy(api_key, pages_per_chunk=10, overlap_pages=2),
    "chunked_5": lambda api_key: ChunkedStrategy(api_key, pages_per_chunk=5, overlap_pages=1),
    # Two-phase extraction
    "two_phase": TwoPhaseStrategy,
    # Model comparison - Gemini 3 variants
    "model_3_pro": lambda api_key: BaselineStrategy(api_key, model="gemini-3-pro-preview"),
    # Legacy models for comparison
    "model_25_pro": lambda api_key: BaselineStrategy(api_key, model="gemini-2.5-pro"),
    "model_25_flash": lambda api_key: BaselineStrategy(api_key, model="gemini-2.5-flash"),
}


def get_strategy(name: str, api_key: str) -> SynthesisStrategy:
    """Get a strategy instance by name."""
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGIES.keys())}")
    
    strategy_cls = STRATEGIES[name]
    if callable(strategy_cls) and not isinstance(strategy_cls, type):
        return strategy_cls(api_key)
    return strategy_cls(api_key)
