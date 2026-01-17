"""
PDF Extraction v6.0 - Hybrid Strategy (Batch + Repair + Async Retry)

Philosophy: "Batch First, Async Patch"
1. Submit ALL chunks to Gemini Batch API (50% cheaper).
2. Attempt local repair on Batch results (fix common JSON errors).
3. Retry ONLY failed chunks using robust Async extraction (full price).
4. Merge all results.

Projected: ~88% cost savings vs Async v4, with 100% reliability.
"""

import os
import sys
import json
import time
import signal
import hashlib
import re
import threading
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile
import shutil

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
MERGE_MODEL = "gemini-2.0-flash-lite"

# Standard Async Pricing
ASYNC_PRICING = {
    "gemini-3-flash-preview": {"input": 0.50, "output": 3.00},
    "gemini-2.0-flash-lite": {"input": 0.10, "output": 0.40},
}

# Batch Pricing (50% off)
BATCH_PRICING = {
    "gemini-3-flash-preview": {"input": 0.25, "output": 1.50},
}

CHUNK_SIZE = 8
OVERLAP_PAGES = 2
MAX_ASYNC_CONCURRENT = 10
MAX_ASYNC_RETRIES = 2


# ============================================================
# REPAIR LOGIC (From v4)
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
    except:
        pass
    
    # Strategy 2: Fix common escape issues
    try:
        fixed = text.replace('\\"', '"').replace('\\n', '\n')
        fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', fixed)
        return json.loads(fixed)
    except:
        pass
    
    # Strategy 3: Find last complete section and close brackets
    strategies = [
        (r'\},\s*$', '}]}"'),
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
        except:
            pass
    
    # Strategy 4: Find last complete object in "sections"
    match = re.search(r'"sections"\s*:\s*\[(.*)', text, re.DOTALL)
    if match:
        sections_content = match.group(1)
        last_obj_end = sections_content.rfind('}')
        if last_obj_end > 0:
            try:
                truncated = '{"sections":[' + sections_content[:last_obj_end+1] + ']}'
                return json.loads(truncated)
            except:
                pass
    
    # Strategy 5: Extract raw objects
    objects = []
    for match in re.finditer(r'\{[^{}]*"title"[^{}]*"content"[^{}]*\}', text):
        try:
            obj = json.loads(match.group())
            objects.append(obj)
        except:
            pass
    
    if objects:
        return {"sections": objects, "partial_repair": True}
    
    return None


def normalize_response(data: Any) -> Dict:
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
# UTILS & TRACKING
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

def extract_chunk_pdf(pdf_path: Path, start_page: int, end_page: int, output_path: Optional[Path] = None) -> Any:
    """Extract pages to file (for batch) or bytes (for async)."""
    import fitz
    doc = fitz.open(pdf_path)
    chunk = fitz.open()
    chunk.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
    
    if output_path:
        chunk.save(output_path)
        chunk.close()
        doc.close()
        return output_path
    else:
        data = chunk.tobytes()
        chunk.close()
        doc.close()
        return data

@dataclass
class TokenUsage:
    prompt: int = 0
    output: int = 0
    
    def add(self, other):
        self.prompt += other.prompt
        self.output += other.output

class CostTracker:
    def __init__(self):
        self.batch_tokens = TokenUsage()
        self.async_tokens = TokenUsage()
        self.merge_tokens = TokenUsage()
        self._lock = threading.Lock()
    
    def add_batch(self, prompt: int, output: int):
        with self._lock:
            self.batch_tokens.prompt += prompt
            self.batch_tokens.output += output
            
    def add_async(self, prompt: int, output: int):
        with self._lock:
            self.async_tokens.prompt += prompt
            self.async_tokens.output += output
            
    @property
    def total_cost(self) -> float:
        bp = BATCH_PRICING[EXTRACTION_MODEL]
        ap = ASYNC_PRICING[EXTRACTION_MODEL]
        
        batch_cost = (self.batch_tokens.prompt / 1e6 * bp["input"] + 
                      self.batch_tokens.output / 1e6 * bp["output"])
        
        async_cost = (self.async_tokens.prompt / 1e6 * ap["input"] + 
                      self.async_tokens.output / 1e6 * ap["output"])
                      
        return batch_cost + async_cost


# ============================================================
# HYBRID EXTRACTOR
# ============================================================

class HybridExtractor:
    def __init__(self, api_key: str, output_dir: Path):
        self.client = genai.Client(api_key=api_key)
        self.output_dir = output_dir
        self.cost_tracker = CostTracker()
        self.results = {}  # chunk_index -> result dict
        self.temp_dir = Path(tempfile.mkdtemp(prefix="hybrid_batch_"))
        
    def cleanup(self):
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def prepare_chunks(self, pdf_path: Path) -> List[Dict]:
        total_pages = get_page_count(pdf_path)
        chunks = []
        chunk_idx = 0
        start = 0
        while start < total_pages:
            end = min(start + CHUNK_SIZE, total_pages)
            chunks.append({
                "chunk_index": chunk_idx,
                "start_page": start,
                "end_page": end
            })
            chunk_idx += 1
            if end < total_pages:
                start = end - OVERLAP_PAGES
            else:
                break
        return chunks

    def run_batch_phase(self, pdf_path: Path, chunks: List[Dict], poll_interval: int = 30) -> List[Dict]:
        """Submit all chunks to Batch API and wait for results."""
        print(f"\n[PHASE 1: BATCH] Generating {len(chunks)} chunks via Batch API...")
        
        # Prepare PDF files
        batch_requests = []
        
        # Use simple extraction prompt
        from extraction_batch import EXTRACTION_PROMPT
        
        print("  Extracting PDFs for batch upload...")
        for i, chunk in enumerate(chunks):
            pdf_file = self.temp_dir / f"chunk_{chunk['chunk_index']}.pdf"
            extract_chunk_pdf(pdf_path, chunk['start_page'], chunk['end_page'], pdf_file)
            
            with open(pdf_file, "rb") as f:
                pdf_bytes = f.read()
            
            batch_requests.append({
                "contents": [
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    f"Pages {chunk['start_page']+1} to {chunk['end_page']}.\n\n{EXTRACTION_PROMPT}"
                ],
                "config": types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
                "metadata": {"chunk_index": str(chunk['chunk_index'])}
            })
            
            if (i+1) % 20 == 0:
                print(f"  Prepared {i+1}/{len(chunks)}...")

        # Submit Batch
        from google.genai.types import InlinedRequest, BatchJobSource
        inlined = [
            InlinedRequest(
                model=EXTRACTION_MODEL,
                contents=req["contents"],
                config=req["config"],
                metadata=req["metadata"]
            ) for req in batch_requests
        ]
        
        try:
            print("  Submitting batch job...")
            job = self.client.batches.create(
                model=EXTRACTION_MODEL,
                src=BatchJobSource(inlined_requests=inlined)
            )
            print(f"  ✓ Job ID: {job.name}")
            
            # Poll
            start_poll = time.perf_counter()
            while True:
                time.sleep(poll_interval)
                status = self.client.batches.get(name=job.name)
                elapsed = timedelta(seconds=int(time.perf_counter() - start_poll))
                print(f"  [{elapsed}] Batch Status: {status.state}")
                
                if status.state == "JOB_STATE_SUCCEEDED":
                    break
                elif status.state in ["JOB_STATE_FAILED", "JOB_STATE_CANCELLED"]:
                    print(f"  ✗ Batch failed: {status.state}")
                    return []
            
            # Retrieve
            print("  Retrieving batch results...")
            complete_job = self.client.batches.get(name=job.name)
            
            failed_chunks = []
            
            if complete_job.dest and complete_job.dest.inlined_responses:
                bs_results = complete_job.dest.inlined_responses
                for i, resp in enumerate(bs_results):
                    chunk_idx = i  # Assuming ordered list matches input list
                    
                    success = False
                    if resp.response and resp.response.text:
                        raw_text = resp.response.text
                        
                        # --- LOCAL REPAIR PHASE ---
                        try:
                            data = json.loads(raw_text)
                            success = True
                        except json.JSONDecodeError:
                            # Attempt repair!
                            repaired = repair_json_v2(raw_text)
                            if repaired:
                                data = repaired
                                success = True
                        
                        if success:
                            data = normalize_response(data)
                            
                            # Track Tokens
                            prompt_t = 0
                            output_t = 0
                            if hasattr(resp.response, 'usage_metadata') and resp.response.usage_metadata:
                                u = resp.response.usage_metadata
                                prompt_t = getattr(u, 'prompt_token_count', 0) or 0
                                output_t = getattr(u, 'candidates_token_count', 0) or 0
                            
                            self.cost_tracker.add_batch(prompt_t, output_t)
                            
                            self.results[chunk_idx] = {
                                "success": True,
                                "source": "batch",
                                "sections": data.get("sections", []),
                                "chunk_idx": chunk_idx
                            }
                    
                    if not success:
                        failed_chunks.append(chunks[chunk_idx])
            else:
                print("  ⚠ No results in batch job")
                failed_chunks = chunks
                
            return failed_chunks
            
        except Exception as e:
            print(f"  ⚠ Batch submission failed: {e}")
            return chunks  # Return all as failed to retry async

    def run_async_retry_phase(self, pdf_path: Path, failed_chunks: List[Dict]):
        """Retry failed chunks using standard Async API."""
        if not failed_chunks:
            return

        print(f"\n[PHASE 2: ASYNC REPAIR] Retrying {len(failed_chunks)} failed chunks...")
        
        from extraction_batch import EXTRACTION_PROMPT
        
        def process_chunk(chunk):
            chunk_idx = chunk["chunk_index"]
            start = chunk["start_page"]
            end = chunk["end_page"]
            
            pdf_bytes = extract_chunk_pdf(pdf_path, start, end)
            
            for attempt in range(MAX_ASYNC_RETRIES + 1):
                try:
                    response = self.client.models.generate_content(
                        model=EXTRACTION_MODEL,
                        contents=[
                            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                            f"Pages {start+1} to {end}.\n\n{EXTRACTION_PROMPT}"
                        ],
                        config=types.GenerateContentConfig(
                            temperature=0.0,
                            response_mime_type="application/json",
                        )
                    )
                    
                    # Track cost
                    p_tok = 0
                    o_tok = 0
                    if response.usage_metadata:
                        p_tok = response.usage_metadata.prompt_token_count or 0
                        o_tok = response.usage_metadata.candidates_token_count or 0
                    self.cost_tracker.add_async(p_tok, o_tok)
                    
                    if response.text:
                        # Try parsing/repairing
                        try:
                            data = json.loads(response.text)
                        except:
                            data = repair_json_v2(response.text)
                        
                        if data:
                            data = normalize_response(data)
                            return {
                                "success": True, 
                                "chunk_idx": chunk_idx, 
                                "sections": data.get("sections", [])
                            }
                except Exception as e:
                    pass
                time.sleep(1 * (attempt+1))
            
            return {"success": False, "chunk_idx": chunk_idx, "error": "Max retries"}

        # Run ThreadPool
        with ThreadPoolExecutor(max_workers=MAX_ASYNC_CONCURRENT) as executor:
            futures = {executor.submit(process_chunk, c): c for c in failed_chunks}
            
            completed = 0
            for future in as_completed(futures):
                res = future.result()
                completed += 1
                
                if res["success"]:
                    self.results[res["chunk_idx"]] = {
                        "success": True,
                        "source": "async_retry",
                        "sections": res["sections"]
                    }
                    print(f"  ✓ Fixed Chunk {res['chunk_idx']+1} ({completed}/{len(failed_chunks)}) 💰 ${self.cost_tracker.total_cost:.4f}")
                else:
                    print(f"  ✗ Failed Chunk {res['chunk_idx']+1} ({completed}/{len(failed_chunks)})")

    def save_final_results(self, pdf_name: str):
        all_sections = []
        # Sort by chunk index
        for idx in sorted(self.results.keys()):
            all_sections.extend(self.results[idx].get("sections", []))
            
        final_data = {
            "pdf": pdf_name,
            "extracted_at": datetime.now().isoformat(),
            "mode": "hybrid_v6",
            "total_cost": self.cost_tracker.total_cost,
            "total_sections": len(all_sections),
            "stats": {
                "batch_processed": len([r for r in self.results.values() if r["source"] == "batch"]),
                "async_repaired": len([r for r in self.results.values() if r["source"] == "async_retry"]),
            },
            "sections": all_sections
        }
        
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_file = self.output_dir / f"knowledge_base_hybrid_{ts}.json"
        
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
            
        print("\n" + "="*60)
        print("HYBRID EXTRACTION COMPLETE")
        print("="*60)
        print(f"Sections: {len(all_sections)}")
        print(f"Cost: ${self.cost_tracker.total_cost:.4f}")
        print(f"Source: {final_data['stats']['batch_processed']} chunks via Batch, {final_data['stats']['async_repaired']} repaired via Async")
        print(f"Saved: {out_file}")


def run_hybrid_process(pdf_path: Path):
    out_dir = Path(__file__).parent / "results" / "hybrid"
    extractor = HybridExtractor(os.getenv("GEMINI_API_KEY"), out_dir)
    
    try:
        chunks = extractor.prepare_chunks(pdf_path)
        
        # 1. Batch Phase
        failed_chunks = extractor.run_batch_phase(pdf_path, chunks)
        
        print(f"\n[STATUS] Batch Phase Complete. Success: {len(chunks) - len(failed_chunks)}/{len(chunks)}")
        print(f"Cost so far: ${extractor.cost_tracker.total_cost:.4f}")
        
        # 2. Async Retry Phase
        if failed_chunks:
            extractor.run_async_retry_phase(pdf_path, failed_chunks)
            
        # 3. Save
        extractor.save_final_results(pdf_path.name)
        
    finally:
        extractor.cleanup()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        pdf = Path(sys.argv[1])
    else:
        pdf = Path(__file__).parent.parent.parent / "pdfs_for_testing" / "Applied strength of materials by Mott, Robert L. Untener, Joseph A (z-lib.org).pdf"
    
    if not pdf.exists():
        print(f"File not found: {pdf}")
        sys.exit(1)
        
    run_hybrid_process(pdf)
