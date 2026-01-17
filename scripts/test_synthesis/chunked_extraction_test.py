"""
Large PDF Chunked Extraction Test with LLM Semantic Merge - v2.0

FIXES from v1:
- Smaller default chunk size (10 pages instead of 15)
- Fixed merge prompt (escaped curly braces)
- Handle Gemini returning list instead of dict
- Better None/empty response handling
- Retry logic for network errors
- JSON repair for truncated responses

Models:
- Chunk Extraction: gemini-3-flash-preview
- Boundary Merge: gemini-2.0-flash-lite (cheapest)
"""

import os
import sys
import json
import time
import hashlib
import tempfile
import re
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sanko-backend"))

from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env")


# ============================================================
# CONFIGURATION
# ============================================================

EXTRACTION_MODEL = "gemini-3-flash-preview"
MERGE_MODEL = "gemini-2.0-flash-lite"

# REDUCED chunk size for better success rate
DEFAULT_CHUNK_SIZE = 10  # was 15
OVERLAP_PAGES = 2  # was 3

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # seconds

# Cost estimates (per 1M tokens)
COSTS = {
    "gemini-3-flash-preview": {"input": 0.10, "output": 0.40},
    "gemini-2.0-flash-lite": {"input": 0.02, "output": 0.08},
}


# ============================================================
# PROMPTS (fixed escaping)
# ============================================================

EXTRACTION_PROMPT = """
You are a STEM content extractor. Extract EXACT, VERBATIM text from this PDF chunk.

Output a JSON object with this EXACT structure:
{{
  "sections": [
    {{
      "title": "Section header",
      "content": "EXACT VERBATIM text - do NOT summarize",
      "visuals": ["Description of diagrams"],
      "page_range": "1-3",
      "is_partial": false,
      "continues_from_previous": false,
      "continues_to_next": false
    }}
  ],
  "chunk_summary": "Brief summary"
}}

CRITICAL RULES:
1. Output ONLY valid JSON - no markdown, no extra text
2. Extract text VERBATIM - never summarize
3. Use LaTeX: $inline$ or $$block$$
4. Mark partial sections appropriately
5. Escape special characters in strings properly
"""

# Use triple-quoted raw string and manual escaping for merge prompt
MERGE_PROMPT_TEMPLATE = '''
You are merging overlapping content from adjacent PDF chunks.

OVERLAP ZONE:
{overlap_content}

TASK:
1. Identify sections split across chunks
2. Merge split sections, remove duplicates
3. Return merged sections as JSON

OUTPUT (valid JSON only):
{{
  "merged_sections": [...],
  "sections_merged_count": 0,
  "duplicate_sentences_removed": 0
}}

RULES:
- Do NOT summarize - preserve verbatim text
- Only merge sections with same topic
- Remove exact duplicate sentences
'''


# ============================================================
# METRICS DATACLASSES
# ============================================================

@dataclass
class ChunkMetrics:
    chunk_index: int
    start_page: int
    end_page: int
    extraction_time_ms: float = 0.0
    response_chars: int = 0
    sections_extracted: int = 0
    success: bool = True
    error: Optional[str] = None
    retries: int = 0
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0


@dataclass
class MergeMetrics:
    boundary_index: int
    merge_time_ms: float = 0.0
    sections_merged: int = 0
    duplicates_removed: int = 0
    success: bool = True
    error: Optional[str] = None
    estimated_input_tokens: int = 0
    estimated_output_tokens: int = 0


@dataclass 
class QualityMetrics:
    total_sections: int = 0
    total_content_chars: int = 0
    avg_section_chars: float = 0.0
    sections_with_visuals: int = 0
    sections_with_latex: int = 0
    sections_with_page_range: int = 0
    empty_sections: int = 0


@dataclass
class CostEstimate:
    extraction_input_tokens: int = 0
    extraction_output_tokens: int = 0
    merge_input_tokens: int = 0
    merge_output_tokens: int = 0
    
    @property
    def extraction_cost(self) -> float:
        costs = COSTS[EXTRACTION_MODEL]
        return (self.extraction_input_tokens * costs["input"] + 
                self.extraction_output_tokens * costs["output"]) / 1_000_000
    
    @property
    def merge_cost(self) -> float:
        costs = COSTS[MERGE_MODEL]
        return (self.merge_input_tokens * costs["input"] + 
                self.merge_output_tokens * costs["output"]) / 1_000_000
    
    @property
    def total_cost(self) -> float:
        return self.extraction_cost + self.merge_cost


@dataclass
class TestResult:
    pdf_name: str
    pdf_size_bytes: int
    pdf_hash: str
    total_pages: int
    chunk_size: int
    overlap_pages: int
    
    total_time_seconds: float = 0.0
    chunk_extraction_time_seconds: float = 0.0
    merge_time_seconds: float = 0.0
    
    total_chunks: int = 0
    successful_chunks: int = 0
    failed_chunks: int = 0
    total_boundaries: int = 0
    total_api_calls: int = 0
    
    chunk_metrics: List[ChunkMetrics] = field(default_factory=list)
    merge_metrics: List[MergeMetrics] = field(default_factory=list)
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    costs: CostEstimate = field(default_factory=CostEstimate)
    
    knowledge_base: Optional[Dict] = None
    success: bool = True
    errors: List[str] = field(default_factory=list)
    
    started_at: str = ""
    completed_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pdf_name": self.pdf_name,
            "pdf_size_mb": round(self.pdf_size_bytes / (1024 * 1024), 2),
            "pdf_hash": self.pdf_hash[:16] + "...",
            "total_pages": self.total_pages,
            "chunk_size": self.chunk_size,
            "overlap_pages": self.overlap_pages,
            "timing": {
                "total_seconds": round(self.total_time_seconds, 2),
                "extraction_seconds": round(self.chunk_extraction_time_seconds, 2),
                "merge_seconds": round(self.merge_time_seconds, 2),
            },
            "counts": {
                "chunks": self.total_chunks,
                "successful_chunks": self.successful_chunks,
                "failed_chunks": self.failed_chunks,
                "success_rate": f"{(self.successful_chunks/self.total_chunks*100):.1f}%" if self.total_chunks > 0 else "0%",
                "boundaries": self.total_boundaries,
                "api_calls": self.total_api_calls,
            },
            "quality": asdict(self.quality),
            "costs": {
                "extraction_cost": f"${self.costs.extraction_cost:.4f}",
                "merge_cost": f"${self.costs.merge_cost:.4f}",
                "total_cost": f"${self.costs.total_cost:.4f}",
            },
            "success": self.success,
            "error_count": len(self.errors),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ============================================================
# UTILITIES
# ============================================================

def hash_pdf(pdf_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_page_count(pdf_path: Path) -> int:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        count = len(doc)
        doc.close()
        return count
    except ImportError:
        raise RuntimeError("PyMuPDF required: pip install PyMuPDF")


def extract_chunk_pdf(pdf_path: Path, start_page: int, end_page: int) -> bytes:
    import fitz
    doc = fitz.open(pdf_path)
    chunk_doc = fitz.open()
    chunk_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
    pdf_bytes = chunk_doc.tobytes()
    chunk_doc.close()
    doc.close()
    return pdf_bytes


def repair_json(text: str) -> Optional[Dict]:
    """Attempt to repair truncated/malformed JSON."""
    if not text:
        return None
    
    # Remove any markdown code blocks
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    
    # Try parsing as-is first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Try to fix common issues
    repaired = text
    
    # Fix unclosed strings
    if repaired.count('"') % 2 != 0:
        repaired += '"'
    
    # Count and close brackets
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')
    
    # Remove trailing comma before closing
    repaired = re.sub(r',\s*$', '', repaired)
    
    # Close brackets
    repaired += ']' * max(0, open_brackets)
    repaired += '}' * max(0, open_braces)
    
    try:
        return json.loads(repaired)
    except json.JSONDecodeError:
        pass
    
    # Last resort: find last complete section
    last_complete = repaired.rfind('},')
    if last_complete > 0:
        candidate = repaired[:last_complete + 1] + ']}'
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    
    return None


def normalize_response(data: Any) -> Dict:
    """Normalize response to expected format."""
    if data is None:
        return {"sections": [], "error": "Empty response"}
    
    # If it's a list, wrap it
    if isinstance(data, list):
        return {"sections": data, "chunk_summary": "Extracted sections"}
    
    # If it's a dict but missing sections key
    if isinstance(data, dict):
        if "sections" not in data:
            # Maybe the whole response is a single section
            if "title" in data and "content" in data:
                return {"sections": [data], "chunk_summary": "Single section"}
        return data
    
    return {"sections": [], "error": f"Unexpected type: {type(data)}"}


# ============================================================
# EXTRACTOR CLASS
# ============================================================

class ChunkedExtractor:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
    
    def extract_chunk(
        self, 
        pdf_bytes: bytes, 
        chunk_index: int,
        start_page: int,
        end_page: int
    ) -> Tuple[Dict, ChunkMetrics]:
        metrics = ChunkMetrics(
            chunk_index=chunk_index,
            start_page=start_page,
            end_page=end_page,
        )
        metrics.estimated_input_tokens = len(pdf_bytes) // 4 + len(EXTRACTION_PROMPT) // 4
        
        last_error = None
        for attempt in range(MAX_RETRIES):
            metrics.retries = attempt
            start_time = time.perf_counter()
            
            try:
                response = self.client.models.generate_content(
                    model=EXTRACTION_MODEL,
                    contents=[
                        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                        f"This is pages {start_page + 1} to {end_page}.\n\n{EXTRACTION_PROMPT}"
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                    )
                )
                
                metrics.extraction_time_ms = (time.perf_counter() - start_time) * 1000
                
                if response.text is None:
                    raise ValueError("Empty response from API")
                
                metrics.response_chars = len(response.text)
                metrics.estimated_output_tokens = metrics.response_chars // 4
                
                # Try to parse, with repair fallback
                try:
                    data = json.loads(response.text)
                except json.JSONDecodeError:
                    data = repair_json(response.text)
                    if data is None:
                        raise
                
                # Normalize the response
                data = normalize_response(data)
                
                sections = data.get("sections", [])
                if isinstance(sections, list):
                    metrics.sections_extracted = len(sections)
                
                metrics.success = True
                return data, metrics
                
            except Exception as e:
                last_error = str(e)
                metrics.extraction_time_ms = (time.perf_counter() - start_time) * 1000
                
                # Check if it's a network error worth retrying
                if any(x in str(e).lower() for x in ['connection', 'timeout', 'network', '10053', '10054', 'getaddrinfo']):
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                
                # For other errors, don't retry
                break
        
        metrics.success = False
        metrics.error = last_error
        return {"sections": [], "error": last_error}, metrics
    
    def merge_boundary(
        self,
        chunk1_last_sections: List[Dict],
        chunk2_first_sections: List[Dict],
        boundary_index: int
    ) -> Tuple[List[Dict], MergeMetrics]:
        metrics = MergeMetrics(boundary_index=boundary_index)
        
        # Skip if nothing to merge
        if not chunk1_last_sections or not chunk2_first_sections:
            metrics.success = True
            return [], metrics
        
        overlap_content = json.dumps({
            "chunk_n_last_sections": chunk1_last_sections,
            "chunk_n_plus_1_first_sections": chunk2_first_sections,
        }, indent=2)
        
        # Use safe string replacement instead of .format()
        prompt = MERGE_PROMPT_TEMPLATE.replace("{overlap_content}", overlap_content)
        metrics.estimated_input_tokens = len(prompt) // 4
        
        start_time = time.perf_counter()
        try:
            response = self.client.models.generate_content(
                model=MERGE_MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            
            metrics.merge_time_ms = (time.perf_counter() - start_time) * 1000
            
            if response.text:
                metrics.estimated_output_tokens = len(response.text) // 4
                
                try:
                    data = json.loads(response.text)
                except json.JSONDecodeError:
                    data = repair_json(response.text)
                
                if data:
                    metrics.sections_merged = data.get("sections_merged_count", 0)
                    metrics.duplicates_removed = data.get("duplicate_sentences_removed", 0)
                    metrics.success = True
                    return data.get("merged_sections", []), metrics
            
            metrics.success = True
            return [], metrics
            
        except Exception as e:
            metrics.merge_time_ms = (time.perf_counter() - start_time) * 1000
            metrics.success = False
            metrics.error = str(e)
            return [], metrics


# ============================================================
# MAIN TEST FUNCTION
# ============================================================

def run_chunked_extraction_test(
    pdf_path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap_pages: int = OVERLAP_PAGES,
    output_dir: Optional[Path] = None,
    skip_merge: bool = False,
) -> TestResult:
    print("=" * 70)
    print("CHUNKED EXTRACTION TEST v2.0")
    print("=" * 70)
    
    result = TestResult(
        pdf_name=pdf_path.name,
        pdf_size_bytes=pdf_path.stat().st_size,
        pdf_hash=hash_pdf(pdf_path),
        total_pages=get_page_count(pdf_path),
        chunk_size=chunk_size,
        overlap_pages=overlap_pages,
        started_at=datetime.now().isoformat(),
    )
    
    print(f"\nPDF: {result.pdf_name}")
    print(f"Size: {result.pdf_size_bytes / (1024*1024):.2f} MB")
    print(f"Pages: {result.total_pages}")
    print(f"Chunk Size: {chunk_size} pages (reduced for reliability)")
    print(f"Overlap: {overlap_pages} pages")
    
    # Calculate chunks
    chunks = []
    start = 0
    while start < result.total_pages:
        end = min(start + chunk_size, result.total_pages)
        chunks.append((start, end))
        if end < result.total_pages:
            start = end - overlap_pages
        else:
            break
    
    result.total_chunks = len(chunks)
    result.total_boundaries = max(0, len(chunks) - 1) if not skip_merge else 0
    result.total_api_calls = result.total_chunks + result.total_boundaries
    
    print(f"Chunks: {result.total_chunks}")
    print(f"Est. API Calls: {result.total_api_calls}")
    print("-" * 70)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    extractor = ChunkedExtractor(api_key)
    all_sections = []
    chunk_results = []
    
    # PHASE 1: Extract chunks
    print("\n[PHASE 1] Extracting chunks...")
    extraction_start = time.perf_counter()
    
    for i, (start_page, end_page) in enumerate(chunks):
        print(f"  Chunk {i+1}/{len(chunks)} (pages {start_page+1}-{end_page})...", end=" ", flush=True)
        
        chunk_bytes = extract_chunk_pdf(pdf_path, start_page, end_page)
        data, metrics = extractor.extract_chunk(chunk_bytes, i, start_page, end_page)
        
        result.chunk_metrics.append(metrics)
        chunk_results.append(data)
        
        result.costs.extraction_input_tokens += metrics.estimated_input_tokens
        result.costs.extraction_output_tokens += metrics.estimated_output_tokens
        
        if metrics.success:
            result.successful_chunks += 1
            retry_info = f" (retry {metrics.retries})" if metrics.retries > 0 else ""
            print(f"OK ({metrics.sections_extracted} sections, {metrics.extraction_time_ms:.0f}ms){retry_info}")
        else:
            result.failed_chunks += 1
            print(f"FAILED: {metrics.error[:60]}...")
            result.errors.append(f"Chunk {i}: {metrics.error}")
    
    result.chunk_extraction_time_seconds = time.perf_counter() - extraction_start
    
    # Summary of Phase 1
    print(f"\n  Phase 1 Complete: {result.successful_chunks}/{result.total_chunks} chunks succeeded ({result.successful_chunks/result.total_chunks*100:.1f}%)")
    
    # PHASE 2: Merge (optional)
    if not skip_merge and result.total_boundaries > 0:
        print("\n[PHASE 2] Merging boundaries...")
        merge_start = time.perf_counter()
        
        successful_merges = 0
        for i in range(len(chunk_results) - 1):
            chunk1_sections = chunk_results[i].get("sections", [])
            chunk2_sections = chunk_results[i+1].get("sections", [])
            
            if not isinstance(chunk1_sections, list):
                chunk1_sections = []
            if not isinstance(chunk2_sections, list):
                chunk2_sections = []
            
            last_sections = chunk1_sections[-2:] if len(chunk1_sections) >= 2 else chunk1_sections
            first_sections = chunk2_sections[:2] if len(chunk2_sections) >= 2 else chunk2_sections
            
            if last_sections and first_sections:
                print(f"  Boundary {i+1}/{result.total_boundaries}...", end=" ", flush=True)
                merged, metrics = extractor.merge_boundary(last_sections, first_sections, i)
                result.merge_metrics.append(metrics)
                
                result.costs.merge_input_tokens += metrics.estimated_input_tokens
                result.costs.merge_output_tokens += metrics.estimated_output_tokens
                
                if metrics.success:
                    successful_merges += 1
                    print(f"OK ({metrics.merge_time_ms:.0f}ms)")
                else:
                    print(f"FAILED: {metrics.error[:40]}...")
        
        result.merge_time_seconds = time.perf_counter() - merge_start
        print(f"\n  Phase 2 Complete: {successful_merges}/{result.total_boundaries} merges succeeded")
    
    # PHASE 3: Combine sections
    print("\n[PHASE 3] Combining sections...")
    for chunk_data in chunk_results:
        sections = chunk_data.get("sections", [])
        if isinstance(sections, list):
            all_sections.extend(sections)
    
    # Quality metrics
    result.quality.total_sections = len(all_sections)
    content_lengths = []
    for section in all_sections:
        if not isinstance(section, dict):
            continue
        content = section.get("content", "")
        if not isinstance(content, str):
            content = str(content) if content else ""
        content_lengths.append(len(content))
        if len(content) == 0:
            result.quality.empty_sections += 1
        if section.get("visuals"):
            result.quality.sections_with_visuals += 1
        if "$" in content or "\\frac" in content:
            result.quality.sections_with_latex += 1
        if section.get("page_range"):
            result.quality.sections_with_page_range += 1
    
    if content_lengths:
        result.quality.total_content_chars = sum(content_lengths)
        result.quality.avg_section_chars = sum(content_lengths) / len(content_lengths)
    
    result.knowledge_base = {
        "summary": f"Extracted from {result.total_pages} pages in {result.total_chunks} chunks",
        "sections": all_sections,
    }
    
    result.total_time_seconds = time.perf_counter() - extraction_start
    result.completed_at = datetime.now().isoformat()
    result.success = result.failed_chunks == 0
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY")
    print("=" * 70)
    print(f"Overall Success: {'YES' if result.success else 'PARTIAL'}")
    print(f"Chunk Success Rate: {result.successful_chunks}/{result.total_chunks} ({result.successful_chunks/result.total_chunks*100:.1f}%)")
    print(f"\nTotal Time: {result.total_time_seconds:.2f} seconds ({result.total_time_seconds/60:.1f} minutes)")
    print(f"  - Extraction: {result.chunk_extraction_time_seconds:.2f}s")
    print(f"  - Merging: {result.merge_time_seconds:.2f}s")
    print(f"\nExtracted:")
    print(f"  - Sections: {result.quality.total_sections}")
    print(f"  - Total Content: {result.quality.total_content_chars:,} chars")
    print(f"  - With LaTeX: {result.quality.sections_with_latex}")
    print(f"  - With Visuals: {result.quality.sections_with_visuals}")
    print(f"\nEstimated Costs:")
    print(f"  - Extraction: ${result.costs.extraction_cost:.4f}")
    print(f"  - Merging: ${result.costs.merge_cost:.4f}")
    print(f"  - TOTAL: ${result.costs.total_cost:.4f}")
    print(f"\nCacheable Hash: {result.pdf_hash[:32]}...")
    print("=" * 70)
    
    # Save results
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        results_file = output_dir / f"test_results_{timestamp}.json"
        with open(results_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to: {results_file}")
        
        kb_file = output_dir / f"knowledge_base_{timestamp}.json"
        with open(kb_file, "w", encoding="utf-8") as f:
            json.dump(result.knowledge_base, f, indent=2, ensure_ascii=False)
        print(f"Knowledge base saved to: {kb_file}")
    
    return result


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Chunked PDF extraction test v2.0")
    parser.add_argument("pdf_path", nargs="?", help="Path to PDF file")
    parser.add_argument("--chunk-size", type=int, default=10, help="Pages per chunk (default: 10)")
    parser.add_argument("--overlap", type=int, default=2, help="Overlap pages (default: 2)")
    parser.add_argument("--output-dir", type=str, help="Output directory")
    parser.add_argument("--skip-merge", action="store_true", help="Skip merge phase (extraction only)")
    
    args = parser.parse_args()
    
    if args.pdf_path:
        pdf_path = Path(args.pdf_path)
    else:
        pdf_path = Path(__file__).parent.parent.parent / "pdfs_for_testing" / "Applied strength of materials by Mott, Robert L. Untener, Joseph A (z-lib.org).pdf"
    
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)
    
    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent / "results" / "chunked_v2"
    
    run_chunked_extraction_test(
        pdf_path=pdf_path,
        chunk_size=args.chunk_size,
        overlap_pages=args.overlap,
        output_dir=output_dir,
        skip_merge=args.skip_merge,
    )
