"""
PDF Extraction v5.0 - Batch Mode

Uses Gemini Batch API for 50% cost savings.
Batch processing is async - submit jobs, poll for completion.

Workflow:
1. Prepare all chunk requests
2. Submit batch job
3. Poll for completion (typically 5-60 min for this size)
4. Retrieve and process results

Models:
- gemini-3-flash-preview: $0.25/M input, $1.50/M output (batch pricing)
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import tempfile

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sanko-backend"))

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")


# ============================================================
# CONFIGURATION
# ============================================================

EXTRACTION_MODEL = "gemini-3-flash-preview"
CHUNK_SIZE = 8
OVERLAP_PAGES = 2

# Batch pricing (50% off)
BATCH_PRICING = {
    "gemini-3-flash-preview": {"input": 0.25, "output": 1.50},
}


# ============================================================
# PROMPTS
# ============================================================

EXTRACTION_PROMPT = """Extract EXACT, VERBATIM content from this PDF as JSON.

Output:
{{
  "sections": [
    {{
      "title": "Section title",
      "content": "VERBATIM text - do NOT summarize",
      "visuals": ["diagram descriptions"],
      "page_range": "1-3"
    }}
  ]
}}

Rules:
1. Valid JSON only
2. VERBATIM extraction - never summarize
3. Include LaTeX: $inline$ or $$block$$
4. Properly escape special characters
"""


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
    import fitz
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count


def extract_chunk_pdf(pdf_path: Path, start_page: int, end_page: int, output_path: Path) -> Path:
    """Extract pages to a temp PDF file for batch processing."""
    import fitz
    doc = fitz.open(pdf_path)
    chunk_doc = fitz.open()
    chunk_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
    chunk_doc.save(output_path)
    chunk_doc.close()
    doc.close()
    return output_path


# ============================================================
# BATCH PROCESSING
# ============================================================

@dataclass
class BatchJob:
    job_id: str
    total_chunks: int
    submitted_at: str
    status: str = "pending"
    results: Optional[Dict] = None


def prepare_batch_requests(pdf_path: Path, chunk_size: int, overlap: int) -> List[Dict]:
    """Prepare all chunk requests for batch submission."""
    total_pages = get_page_count(pdf_path)
    
    requests = []
    chunk_idx = 0
    start = 0
    
    while start < total_pages:
        end = min(start + chunk_size, total_pages)
        
        requests.append({
            "chunk_index": chunk_idx,
            "start_page": start,
            "end_page": end,
        })
        
        chunk_idx += 1
        if end < total_pages:
            start = end - overlap
        else:
            break
    
    return requests


def run_batch_extraction(
    pdf_path: Path,
    output_dir: Optional[Path] = None,
    chunk_size: int = CHUNK_SIZE,
    poll_interval: int = 30,
) -> Dict:
    """
    Run batch extraction with Gemini Batch API.
    
    This is an async process:
    1. Submit all chunks as a batch
    2. Poll for completion
    3. Process results
    """
    
    print("=" * 70)
    print("PDF EXTRACTION v5.0 (Batch Mode - 50% Cheaper)")
    print("=" * 70)
    
    # Setup
    total_pages = get_page_count(pdf_path)
    pdf_hash = hash_pdf(pdf_path)[:16]
    output_dir = output_dir or Path(__file__).parent / "results" / "batch"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    client = genai.Client(api_key=api_key)
    
    print(f"\nPDF: {pdf_path.name}")
    print(f"Pages: {total_pages}")
    print(f"Chunk Size: {chunk_size}")
    print("-" * 70)
    
    # Prepare requests
    chunk_requests = prepare_batch_requests(pdf_path, chunk_size, OVERLAP_PAGES)
    print(f"Total chunks: {len(chunk_requests)}")
    
    # Create temp directory for chunk PDFs
    temp_dir = Path(tempfile.mkdtemp(prefix="gemini_batch_"))
    print(f"Temp dir: {temp_dir}")
    
    # Prepare inline requests for batch
    print(f"\n[PREPARING] Extracting {len(chunk_requests)} chunk PDFs...")
    
    batch_requests = []
    for req in chunk_requests:
        chunk_pdf_path = temp_dir / f"chunk_{req['chunk_index']}.pdf"
        extract_chunk_pdf(pdf_path, req['start_page'], req['end_page'], chunk_pdf_path)
        
        # Read chunk as bytes
        with open(chunk_pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        batch_requests.append({
            "contents": [
                types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                f"Pages {req['start_page'] + 1} to {req['end_page']}.\n\n{EXTRACTION_PROMPT}"
            ],
            "config": types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
            ),
        })
        
        if (req['chunk_index'] + 1) % 20 == 0:
            print(f"  Prepared {req['chunk_index'] + 1}/{len(chunk_requests)} chunks...")
    
    print(f"  ✓ All {len(chunk_requests)} chunks prepared")
    
    # Submit batch job
    print(f"\n[SUBMITTING] Creating batch job...")
    start_time = time.perf_counter()
    
    try:
        # Build proper InlinedRequest objects for batch
        from google.genai.types import InlinedRequest, BatchJobSource
        
        inlined_requests = []
        for i, req in enumerate(batch_requests):
            ir = InlinedRequest(
                model=EXTRACTION_MODEL,
                contents=req["contents"],
                config=req["config"],
                metadata={"chunk_index": str(i)},
            )
            inlined_requests.append(ir)
        
        # Create batch source with inlined requests
        src = BatchJobSource(inlined_requests=inlined_requests)
        
        # Use batches API
        batch_job = client.batches.create(
            model=EXTRACTION_MODEL,
            src=src,
        )
        
        job_id = batch_job.name
        print(f"  ✓ Batch job created: {job_id}")
        
    except Exception as e:
        # Fallback: If batch API not available, use concurrent async
        print(f"  ⚠ Batch API error: {e}")
        print(f"  → Falling back to high-concurrency async mode")
        return run_fallback_async(pdf_path, chunk_requests, client, output_dir)
    
    # Poll for completion
    print(f"\n[WAITING] Polling every {poll_interval}s for completion...")
    print("  (Batch jobs typically complete in 5-60 minutes)")
    
    while True:
        time.sleep(poll_interval)
        
        status = client.batches.get(name=job_id)
        elapsed = time.perf_counter() - start_time
        
        print(f"  [{timedelta(seconds=int(elapsed))}] Status: {status.state}")
        
        if status.state == "JOB_STATE_SUCCEEDED":
            print(f"  ✓ Batch completed!")
            break
        elif status.state in ["JOB_STATE_FAILED", "JOB_STATE_CANCELLED"]:
            print(f"  ✗ Batch failed: {status.state}")
            return {"success": False, "error": status.state}
    
    # Retrieve results - get final batch job status
    print(f"\n[RETRIEVING] Getting results...")
    
    # Fetch the completed batch job with results
    completed_job = client.batches.get(name=job_id)
    
    # Process results from dest.inlined_responses
    all_sections = []
    successful = 0
    failed = 0
    total_input_tokens = 0
    total_output_tokens = 0
    
    if completed_job.dest and completed_job.dest.inlined_responses:
        results = completed_job.dest.inlined_responses
        print(f"  Found {len(results)} responses")
        
        for i, result in enumerate(results):
            try:
                # InlinedResponse has 'response' which is a GenerateContentResponse
                if result.response and result.response.text:
                    data = json.loads(result.response.text)
                    sections = data.get("sections", [])
                    all_sections.extend(sections)
                    successful += 1
                    
                    # Track tokens
                    if hasattr(result.response, 'usage_metadata') and result.response.usage_metadata:
                        total_input_tokens += getattr(result.response.usage_metadata, 'prompt_token_count', 0) or 0
                        total_output_tokens += getattr(result.response.usage_metadata, 'candidates_token_count', 0) or 0
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                if i < 5:  # Log first few errors
                    print(f"    Chunk {i}: Error - {str(e)[:50]}")
    else:
        print("  ⚠ No inlined responses found")
    
    total_time = time.perf_counter() - start_time
    
    # Calculate cost (batch pricing = 50% off)
    pricing = BATCH_PRICING[EXTRACTION_MODEL]
    cost = (total_input_tokens / 1e6 * pricing["input"] + 
            total_output_tokens / 1e6 * pricing["output"])
    
    # Save knowledge base
    kb = {
        "pdf": pdf_path.name,
        "extracted_at": datetime.now().isoformat(),
        "mode": "batch",
        "total_sections": len(all_sections),
        "sections": all_sections,
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    kb_file = output_dir / f"knowledge_base_batch_{timestamp}.json"
    with open(kb_file, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
    
    # Cleanup temp files
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    
    # Summary
    print("\n" + "=" * 70)
    print("RESULTS (Batch Mode)")
    print("=" * 70)
    print(f"Success: {successful}/{len(chunk_requests)} chunks")
    print(f"Sections: {len(all_sections)}")
    print(f"Time: {total_time/60:.1f} min")
    print(f"Tokens: {total_input_tokens:,} in, {total_output_tokens:,} out")
    print(f"Cost: ${cost:.2f} (50% batch discount applied)")
    print(f"\n✅ Saved: {kb_file}")
    print("=" * 70)
    
    return {
        "success": True,
        "chunks": successful,
        "sections": len(all_sections),
        "cost": cost,
        "time_min": total_time / 60,
        "output": str(kb_file),
    }


def run_fallback_async(pdf_path: Path, chunk_requests: List[Dict], 
                       client, output_dir: Path) -> Dict:
    """Fallback to high-concurrency async if batch API isn't available."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    print("\n[FALLBACK] Running high-concurrency async (20 parallel)...")
    
    def process_chunk(req: Dict) -> Dict:
        import fitz
        doc = fitz.open(pdf_path)
        chunk_doc = fitz.open()
        chunk_doc.insert_pdf(doc, from_page=req['start_page'], to_page=req['end_page'] - 1)
        pdf_bytes = chunk_doc.tobytes()
        chunk_doc.close()
        doc.close()
        
        try:
            response = client.models.generate_content(
                model=EXTRACTION_MODEL,
                contents=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    f"Pages {req['start_page'] + 1} to {req['end_page']}.\n\n{EXTRACTION_PROMPT}"
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            
            if response.text:
                data = json.loads(response.text)
                return {"success": True, "sections": data.get("sections", [])}
        except Exception as e:
            pass
        
        return {"success": False, "sections": []}
    
    all_sections = []
    successful = 0
    start_time = time.perf_counter()
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(process_chunk, req): req for req in chunk_requests}
        
        for i, future in enumerate(as_completed(futures)):
            result = future.result()
            if result["success"]:
                all_sections.extend(result["sections"])
                successful += 1
            
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(chunk_requests)}] {successful} successful")
    
    total_time = time.perf_counter() - start_time
    
    # Save
    kb = {
        "pdf": pdf_path.name,
        "mode": "async_fallback",
        "total_sections": len(all_sections),
        "sections": all_sections,
    }
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    kb_file = output_dir / f"knowledge_base_async_{timestamp}.json"
    with open(kb_file, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Fallback complete: {successful}/{len(chunk_requests)} chunks")
    print(f"Time: {total_time/60:.1f} min")
    print(f"Saved: {kb_file}")
    
    return {"success": True, "chunks": successful, "output": str(kb_file)}


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF Extraction v5.0 (Batch)")
    parser.add_argument("pdf_path", nargs="?")
    parser.add_argument("--chunk-size", type=int, default=8)
    parser.add_argument("--poll-interval", type=int, default=30, help="Seconds between status checks")
    parser.add_argument("--output-dir", type=str)
    
    args = parser.parse_args()
    
    if args.pdf_path:
        pdf_path = Path(args.pdf_path)
    else:
        pdf_path = Path(__file__).parent.parent.parent / "pdfs_for_testing" / "Applied strength of materials by Mott, Robert L. Untener, Joseph A (z-lib.org).pdf"
    
    if not pdf_path.exists():
        print(f"ERROR: {pdf_path}")
        sys.exit(1)
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    run_batch_extraction(
        pdf_path=pdf_path,
        output_dir=output_dir,
        chunk_size=args.chunk_size,
        poll_interval=args.poll_interval,
    )
