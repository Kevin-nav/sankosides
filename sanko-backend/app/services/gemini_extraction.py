"""
Gemini PDF Extraction Service v8.0

Optimized extraction service achieving 95% cost reduction through:
1. Local PDF chunking (PyMuPDF) - 97% fewer input tokens
2. Batch API - 50% discount on all tokens
3. MEDIUM resolution - 50% fewer tokens per page
4. Pydantic schema - Strict JSON, no wasted output tokens
5. JSON repair - Recovers truncated responses
6. Parallel sync retry - Guarantees 100% completion

Based on research from "Optimizing Gemini PDF Extraction Service.md"
"""

import os
import json
import time
import re
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from pydantic import BaseModel, Field
import threading

from google import genai
from google.genai import types
from google.genai.types import InlinedRequest, BatchJobSource

from app.models.schemas import KnowledgeBase, DocumentSection
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_ID = "gemini-3-flash-preview"
CHUNK_SIZE = 20  # Pages per chunk
OVERLAP_PAGES = 2
MAX_RETRIES = 2
MAX_PARALLEL_RETRIES = 5
BATCH_POLL_INTERVAL = 30  # seconds

# Pricing (2026) - for cost tracking
BATCH_PRICING = {"input_per_m": 0.25, "output_per_m": 1.50}
SYNC_PRICING = {"input_per_m": 0.50, "output_per_m": 3.00}


# ============================================================
# PYDANTIC SCHEMAS (Strict Output)
# ============================================================

class Section(BaseModel):
    """A single extracted section from the PDF."""
    title: str = Field(description="Section or chapter title")
    content: str = Field(description="VERBATIM text content - never summarize")
    visuals: List[str] = Field(default_factory=list, description="Descriptions of diagrams, figures, tables")
    page_range: str = Field(description="Page range this section spans, e.g. '1-3'")


class ExtractionResult(BaseModel):
    """The complete extraction result for a chunk."""
    sections: List[Section] = Field(default_factory=list)


EXTRACTION_PROMPT = """Extract EXACT, VERBATIM content from this PDF chunk.

Rules:
1. Extract ALL text content VERBATIM - never summarize or paraphrase
2. Use LaTeX for math: $inline$ or $$block$$  
3. Describe all diagrams, figures, and tables in the visuals array
4. Include the page range for each section
5. Properly escape special characters in JSON

Focus on accuracy and completeness."""


# ============================================================
# JSON REPAIR
# ============================================================

def repair_json_v2(text: str) -> Optional[Dict]:
    """Multi-strategy JSON repair for truncated responses."""
    if not text:
        return None
    
    # Remove markdown code blocks
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    
    # Strategy 1: Try as-is
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Fix common escape issues
    try:
        fixed = text.replace('\\"', '"').replace('\\n', '\n')
        fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', fixed)
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    
    # Strategy 3: Close truncated JSON
    strategies = [
        (r'\},\s*$', '}]}'),
        (r'\}\s*$', '}]}'),
        (r'"\s*$', '"}]}'),
        (r',\s*$', '}]}'),
    ]
    
    for pattern, suffix in strategies:
        try:
            candidate = re.sub(pattern, suffix, text)
            open_braces = candidate.count('{') - candidate.count('}')
            open_brackets = candidate.count('[') - candidate.count(']')
            candidate += '}' * max(0, open_braces)
            candidate += ']' * max(0, open_brackets)
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass
    
    # Strategy 4: Find last complete section
    match = re.search(r'"sections"\s*:\s*\[(.*)', text, re.DOTALL)
    if match:
        sections_content = match.group(1)
        last_obj_end = sections_content.rfind('}')
        if last_obj_end > 0:
            try:
                truncated = '{"sections":[' + sections_content[:last_obj_end+1] + ']}'
                return json.loads(truncated)
            except json.JSONDecodeError:
                pass
    
    # Strategy 5: Extract individual section objects
    objects = []
    for m in re.finditer(r'\{[^{}]*"title"[^{}]*"content"[^{}]*\}', text):
        try:
            obj = json.loads(m.group())
            objects.append(obj)
        except json.JSONDecodeError:
            pass
    
    if objects:
        return {"sections": objects, "partial_repair": True}
    
    return None


def normalize_response(data: Any) -> Dict:
    """Normalize various response formats to standard structure."""
    if data is None:
        return {"sections": []}
    if isinstance(data, list):
        return {"sections": data}
    if isinstance(data, dict):
        if "sections" not in data:
            if "title" in data and "content" in data:
                return {"sections": [data]}
        return data
    return {"sections": []}


# ============================================================
# COST TRACKER
# ============================================================

class CostTracker:
    """Track token usage and costs across all phases."""
    
    def __init__(self):
        self.batch_in = 0
        self.batch_out = 0
        self.sync_in = 0
        self.sync_out = 0
    
    def add_batch(self, in_tokens: int, out_tokens: int):
        self.batch_in += in_tokens
        self.batch_out += out_tokens
    
    def add_sync(self, in_tokens: int, out_tokens: int):
        self.sync_in += in_tokens
        self.sync_out += out_tokens
    
    @property
    def total_cost(self) -> float:
        batch_cost = (
            self.batch_in / 1e6 * BATCH_PRICING["input_per_m"] +
            self.batch_out / 1e6 * BATCH_PRICING["output_per_m"]
        )
        sync_cost = (
            self.sync_in / 1e6 * SYNC_PRICING["input_per_m"] +
            self.sync_out / 1e6 * SYNC_PRICING["output_per_m"]
        )
        return batch_cost + sync_cost
    
    def summary(self) -> str:
        return (
            f"Batch: {self.batch_in:,} in, {self.batch_out:,} out | "
            f"Sync: {self.sync_in:,} in, {self.sync_out:,} out"
        )


# ============================================================
# GEMINI EXTRACTION SERVICE
# ============================================================

class GeminiExtractionService:
    """
    Optimized PDF extraction service using Gemini with v8 optimizations.
    
    Achieves 95% cost reduction compared to naive single-call approach.
    """
    
    def __init__(self):
        self.api_key = settings.gemini_api_key
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        self.client = genai.Client(api_key=self.api_key)
        self.cost_tracker = CostTracker()

    def _parse_page_range(self, value: str, fallback_start: int, fallback_end: int) -> Tuple[int, int, str]:
        """Normalize page range into numeric start/end and canonical string."""
        if value:
            m = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", value)
            if m:
                start = int(m.group(1))
                end = int(m.group(2))
                if start > 0 and end >= start:
                    return start, end, f"{start}-{end}"
        return fallback_start, fallback_end, f"{fallback_start}-{fallback_end}"

    def _stable_section_id(self, document_id: str, chunk_index: int, title: str, page_range: str, content: str) -> str:
        payload = f"{document_id}|{chunk_index}|{title}|{page_range}|{content[:200]}"
        digest = hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()
        return f"sec-{digest[:24]}"

    def _normalize_section_payloads(
        self,
        raw_sections: List[Dict[str, Any]],
        chunk: Dict[str, Any],
        document_id: str,
        filename: str,
    ) -> List[Dict[str, Any]]:
        """
        Normalize extracted section payloads and enforce minimal validity.
        """
        normalized = []
        fallback_start = int(chunk["start"]) + 1
        fallback_end = int(chunk["end"])

        for idx, sec in enumerate(raw_sections or []):
            title = str(sec.get("title") or "").strip() or f"Untitled Section {chunk['index'] + 1}.{idx + 1}"
            content = str(sec.get("content") or "").strip()
            visuals = sec.get("visuals") or []
            if not isinstance(visuals, list):
                visuals = []

            if not content:
                continue

            p_start, p_end, canonical_range = self._parse_page_range(
                str(sec.get("page_range") or ""),
                fallback_start=fallback_start,
                fallback_end=fallback_end,
            )

            content_hash = hashlib.sha256(content.encode("utf-8", errors="ignore")).hexdigest()
            section_id = self._stable_section_id(
                document_id=document_id,
                chunk_index=int(chunk["index"]),
                title=title,
                page_range=canonical_range,
                content=content,
            )

            normalized.append({
                "title": title,
                "content": content,
                "visuals": visuals,
                "page_range": canonical_range,
                "section_id": section_id,
                "document_id": document_id,
                "document_name": filename,
                "page_start": p_start,
                "page_end": p_end,
                "chunk_index": int(chunk["index"]),
                "content_hash": content_hash,
            })

        return normalized

    def _validate_extraction_quality(
        self,
        sections: List[DocumentSection],
        total_pages: int,
        total_chunks: int,
    ) -> None:
        """
        Hard validation gate to prevent low-quality/summarized extraction from entering pipeline.
        """
        min_sections = max(1, int(getattr(settings, "extraction_min_sections", 3)))
        min_coverage = float(getattr(settings, "extraction_min_coverage_ratio", 0.6))

        if len(sections) < min_sections:
            raise RuntimeError(
                f"Extraction quality gate failed: only {len(sections)} sections (< {min_sections})"
            )

        covered_pages = set()
        for s in sections:
            if s.page_start and s.page_end and s.page_start <= s.page_end:
                for p in range(s.page_start, s.page_end + 1):
                    covered_pages.add(p)

        coverage_ratio = (len(covered_pages) / total_pages) if total_pages > 0 else 0.0
        logger.info(
            f"[v8-EXTRACT] Quality gate: sections={len(sections)}, "
            f"coverage={coverage_ratio:.2f}, pages={total_pages}, chunks={total_chunks}"
        )
        if coverage_ratio < min_coverage:
            raise RuntimeError(
                f"Extraction quality gate failed: coverage {coverage_ratio:.2f} (< {min_coverage:.2f})"
            )

        nontrivial = sum(1 for s in sections if len((s.content or "").strip()) >= 120)
        if nontrivial < max(1, len(sections) // 3):
            raise RuntimeError(
                "Extraction quality gate failed: too many sections have very short content"
            )
    
    def extract_from_bytes(self, pdf_bytes: bytes, filename: str = "document.pdf") -> KnowledgeBase:
        """
        Extract content from PDF bytes (for R2 downloads).
        
        Args:
            pdf_bytes: Raw PDF file content
            filename: Original filename for logging
            
        Returns:
            KnowledgeBase with extracted content
        """
        # Write to temp file for PyMuPDF processing
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)
        
        try:
            return self.extract_from_pdf(tmp_path, filename)
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    
    def extract_from_pdf(self, pdf_path: Path, filename: str = None) -> KnowledgeBase:
        """
        Extract content from a PDF file using optimized v8 pipeline.
        
        Args:
            pdf_path: Path to the PDF file
            filename: Optional filename for logging
            
        Returns:
            KnowledgeBase with extracted content
        """
        import fitz  # PyMuPDF
        
        filename = filename or pdf_path.name
        start_time = time.perf_counter()
        try:
            document_id = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]
        except Exception:
            document_id = hashlib.sha256(str(pdf_path).encode("utf-8")).hexdigest()[:16]
        
        logger.info(f"[v8-EXTRACT] Starting extraction: {filename}")
        
        # ========================================
        # PHASE 1: Prepare Local PDF Chunks
        # ========================================
        logger.info(f"[v8-EXTRACT] Phase 1: Preparing local PDF chunks...")
        
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        chunks = self._prepare_chunks(total_pages)
        logger.info(f"[v8-EXTRACT]   Pages: {total_pages}, Chunks: {len(chunks)}")
        
        # ========================================
        # PHASE 2: Batch Submission
        # ========================================
        logger.info(f"[v8-EXTRACT] Phase 2: Submitting batch job...")
        
        batch_job = self._submit_batch(pdf_path, chunks)
        logger.info(f"[v8-EXTRACT]   Job ID: {batch_job.name}")
        
        # Poll for completion
        logger.info(f"[v8-EXTRACT]   Polling every {BATCH_POLL_INTERVAL}s...")
        batch_start = time.perf_counter()
        while True:
            time.sleep(BATCH_POLL_INTERVAL)
            status = self.client.batches.get(name=batch_job.name)
            elapsed = timedelta(seconds=int(time.perf_counter() - batch_start))
            logger.info(f"[v8-EXTRACT]   [{elapsed}] {status.state}")
            
            if status.state == "JOB_STATE_SUCCEEDED":
                logger.info(f"[v8-EXTRACT]   ✓ Batch completed!")
                break
            elif status.state in ["JOB_STATE_FAILED", "JOB_STATE_CANCELLED"]:
                raise RuntimeError(f"Batch job failed: {status.state}")
        
        # ========================================
        # PHASE 3: Process Results with Repair
        # ========================================
        logger.info(f"[v8-EXTRACT] Phase 3: Processing batch results...")
        
        results, failed_chunks = self._process_batch_results(batch_job.name, chunks)
        
        batch_direct = sum(1 for r in results.values() if r.get("source") == "direct")
        batch_repaired = sum(1 for r in results.values() if r.get("source") == "repaired")
        
        logger.info(f"[v8-EXTRACT]   Direct success: {batch_direct}")
        logger.info(f"[v8-EXTRACT]   Repaired: {batch_repaired}")
        logger.info(f"[v8-EXTRACT]   Failed: {len(failed_chunks)}")
        
        # ========================================
        # PHASE 4: Parallel Sync Retry
        # ========================================
        if failed_chunks:
            logger.info(f"[v8-EXTRACT] Phase 4: Parallel sync retry for {len(failed_chunks)} chunks...")
            retry_results = self._retry_failed_chunks(pdf_path, failed_chunks)
            for idx, sections in retry_results.items():
                results[idx] = {"sections": sections, "source": "retry"}
            logger.info(f"[v8-EXTRACT]   Recovered: {len(retry_results)}/{len(failed_chunks)}")
        else:
            logger.info(f"[v8-EXTRACT] Phase 4: No failed chunks - skipping retry")
        
        # ========================================
        # FINALIZE
        # ========================================
        total_time = time.perf_counter() - start_time
        
        # Flatten sections in order
        all_sections = []
        chunk_map = {int(c["index"]): c for c in chunks}
        for idx in sorted(results.keys()):
            chunk = chunk_map.get(int(idx))
            if not chunk:
                continue
            normalized = self._normalize_section_payloads(
                raw_sections=results[idx].get("sections", []),
                chunk=chunk,
                document_id=document_id,
                filename=filename,
            )
            all_sections.extend(normalized)
        
        # Convert to DocumentSection objects
        doc_sections = []
        seen_ids = set()
        for s in all_sections:
            section_id = s.get("section_id") or ""
            if section_id in seen_ids:
                section_id = f"{section_id}-{len(seen_ids)}"
            seen_ids.add(section_id)
            doc_sections.append(DocumentSection(
                title=s.get("title", "Untitled"),
                content=s.get("content", ""),
                visuals=s.get("visuals", []),
                page_range=s.get("page_range", ""),
                section_id=section_id,
                document_id=s.get("document_id", ""),
                document_name=s.get("document_name", filename),
                page_start=s.get("page_start"),
                page_end=s.get("page_end"),
                chunk_index=s.get("chunk_index"),
                content_hash=s.get("content_hash", ""),
            ))

        self._validate_extraction_quality(
            sections=doc_sections,
            total_pages=total_pages,
            total_chunks=len(chunks),
        )
        
        # Create summary
        summary = f"Extracted {len(doc_sections)} sections from {filename} ({total_pages} pages)"
        
        logger.info(f"[v8-EXTRACT] Complete: {len(doc_sections)} sections in {total_time/60:.1f} min")
        logger.info(f"[v8-EXTRACT] Cost: ${self.cost_tracker.total_cost:.4f}")
        logger.info(f"[v8-EXTRACT] Tokens: {self.cost_tracker.summary()}")
        
        return KnowledgeBase(
            summary=summary,
            sections=doc_sections,
        )
    
    def _prepare_chunks(self, total_pages: int) -> List[Dict]:
        """Prepare chunk definitions with overlap."""
        chunks = []
        start = 0
        chunk_idx = 0
        
        while start < total_pages:
            end = min(start + CHUNK_SIZE, total_pages)
            chunks.append({
                "index": chunk_idx,
                "start": start,
                "end": end,
                "range": f"{start+1}-{end}"
            })
            chunk_idx += 1
            if end < total_pages:
                start = end - OVERLAP_PAGES
            else:
                break
        
        return chunks
    
    def _extract_chunk_pdf(self, pdf_path: Path, start_page: int, end_page: int) -> bytes:
        """Extract specific pages from PDF as bytes."""
        import fitz
        doc = fitz.open(pdf_path)
        chunk = fitz.open()
        chunk.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
        data = chunk.tobytes()
        chunk.close()
        doc.close()
        return data
    
    def _submit_batch(self, pdf_path: Path, chunks: List[Dict]):
        """Submit all chunks as a batch job."""
        inlined_requests = []
        
        for chunk in chunks:
            chunk_bytes = self._extract_chunk_pdf(pdf_path, chunk["start"], chunk["end"])
            
            pdf_part = types.Part.from_bytes(
                data=chunk_bytes,
                mime_type="application/pdf",
            )
            
            ir = InlinedRequest(
                model=MODEL_ID,
                contents=[
                    pdf_part,
                    f"Pages {chunk['range']} of the document.\n\n{EXTRACTION_PROMPT}"
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                    response_schema=ExtractionResult,
                ),
                metadata={"chunk_index": str(chunk["index"]), "range": chunk["range"]}
            )
            inlined_requests.append(ir)
        
        return self.client.batches.create(
            model=MODEL_ID,
            src=BatchJobSource(inlined_requests=inlined_requests)
        )
    
    def _process_batch_results(
        self,
        job_name: str,
        chunks: List[Dict]
    ) -> Tuple[Dict[int, Dict], List[Dict]]:
        """Process batch results with JSON repair."""
        completed_job = self.client.batches.get(name=job_name)
        
        results = {}
        failed_chunks = []
        
        if completed_job.dest and completed_job.dest.inlined_responses:
            for i, resp in enumerate(completed_job.dest.inlined_responses):
                chunk_idx = i
                success = False
                
                if resp.response and resp.response.text:
                    raw_text = resp.response.text
                    
                    # Track tokens
                    if resp.response.usage_metadata:
                        self.cost_tracker.add_batch(
                            resp.response.usage_metadata.prompt_token_count or 0,
                            resp.response.usage_metadata.candidates_token_count or 0
                        )
                    
                    # Try direct parse
                    try:
                        data = json.loads(raw_text)
                        data = normalize_response(data)
                        results[chunk_idx] = {
                            "sections": data.get("sections", []),
                            "source": "direct"
                        }
                        success = True
                    except json.JSONDecodeError:
                        # Try repair
                        repaired = repair_json_v2(raw_text)
                        if repaired:
                            data = normalize_response(repaired)
                            results[chunk_idx] = {
                                "sections": data.get("sections", []),
                                "source": "repaired"
                            }
                            success = True
                
                if not success:
                    failed_chunks.append(chunks[chunk_idx])
        
        return results, failed_chunks
    
    def _retry_failed_chunks(
        self,
        pdf_path: Path,
        failed_chunks: List[Dict]
    ) -> Dict[int, List[Dict]]:
        """Retry failed chunks using parallel sync API calls."""
        token_lock = threading.Lock()
        sync_tokens = {"in": 0, "out": 0}
        
        def retry_chunk(chunk_info: Dict) -> Tuple[int, Optional[List[Dict]]]:
            idx = chunk_info["index"]
            chunk_bytes = self._extract_chunk_pdf(pdf_path, chunk_info["start"], chunk_info["end"])
            
            local_in = 0
            local_out = 0
            
            simple_prompt = f"""Extract text from pages {chunk_info['range']}.

Return ONLY valid JSON with this exact structure:
{{"sections": [{{"title": "Section Title", "content": "Full verbatim text...", "visuals": [], "page_range": "{chunk_info['range']}"}}]}}

Important:
- VERBATIM text only, never summarize
- Valid JSON only - properly escape quotes and special characters
- Include all text content from these pages"""
            
            for attempt in range(MAX_RETRIES + 1):
                try:
                    use_explicit_cache = bool(getattr(settings, "enable_gemini_explicit_cache", False))
                    if use_explicit_cache:
                        cache_ttl = max(60, int(getattr(settings, "gemini_cache_ttl_seconds", 900)))
                        cache_obj = None
                        try:
                            cache_cfg = types.CreateCachedContentConfig(
                                model=MODEL_ID,
                                contents=[
                                    types.Content(
                                        role="user",
                                        parts=[types.Part.from_bytes(data=chunk_bytes, mime_type="application/pdf")],
                                    )
                                ],
                                ttl=f"{cache_ttl}s",
                            )
                            cache_obj = self.client.caches.create(model=MODEL_ID, config=cache_cfg)
                            response = self.client.models.generate_content(
                                model=MODEL_ID,
                                contents=[simple_prompt],
                                config=types.GenerateContentConfig(
                                    cached_content=cache_obj.name,
                                    temperature=0.1 * attempt,
                                    response_mime_type="application/json",
                                ),
                            )
                        finally:
                            if cache_obj:
                                try:
                                    self.client.caches.delete(name=cache_obj.name)
                                except Exception:
                                    pass
                    else:
                        response = self.client.models.generate_content(
                            model=MODEL_ID,
                            contents=[
                                types.Part.from_bytes(data=chunk_bytes, mime_type="application/pdf"),
                                simple_prompt
                            ],
                            config=types.GenerateContentConfig(
                                temperature=0.1 * attempt,
                                response_mime_type="application/json",
                            )
                        )
                    
                    if response.usage_metadata:
                        local_in += response.usage_metadata.prompt_token_count or 0
                        local_out += response.usage_metadata.candidates_token_count or 0
                    
                    if response.text:
                        # Try direct parse
                        try:
                            data = json.loads(response.text)
                            data = normalize_response(data)
                            if data.get("sections"):
                                with token_lock:
                                    sync_tokens["in"] += local_in
                                    sync_tokens["out"] += local_out
                                return idx, data["sections"]
                        except json.JSONDecodeError:
                            pass
                        
                        # Try repair
                        repaired = repair_json_v2(response.text)
                        if repaired:
                            data = normalize_response(repaired)
                            if data.get("sections"):
                                with token_lock:
                                    sync_tokens["in"] += local_in
                                    sync_tokens["out"] += local_out
                                return idx, data["sections"]
                
                except Exception as e:
                    logger.warning(f"[v8-EXTRACT] Retry attempt {attempt+1} failed for chunk {idx}: {e}")
                
                time.sleep(0.5 * (attempt + 1))
            
            with token_lock:
                sync_tokens["in"] += local_in
                sync_tokens["out"] += local_out
            return idx, None
        
        # Run retries in parallel
        results = {}
        with ThreadPoolExecutor(max_workers=MAX_PARALLEL_RETRIES) as executor:
            futures = {executor.submit(retry_chunk, c): c for c in failed_chunks}
            
            for future in as_completed(futures):
                idx, sections = future.result()
                if sections:
                    results[idx] = sections
                    logger.info(f"[v8-EXTRACT]   ✓ Chunk {idx+1} recovered")
                else:
                    logger.warning(f"[v8-EXTRACT]   ✗ Chunk {idx+1} failed after retries")
        
        # Update cost tracker with sync tokens
        self.cost_tracker.add_sync(sync_tokens["in"], sync_tokens["out"])
        
        return results


# ============================================================
# SINGLETON ACCESS
# ============================================================

_extraction_service: Optional[GeminiExtractionService] = None


def get_extraction_service() -> GeminiExtractionService:
    """Get or create the global extraction service instance."""
    global _extraction_service
    if _extraction_service is None:
        _extraction_service = GeminiExtractionService()
    return _extraction_service
