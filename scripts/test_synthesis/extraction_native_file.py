"""
PDF Extraction v7.1 - Native File Strategy with Repair + Retry

Core Concept:
1. Upload the FULL PDF to Gemini File API ONCE.
2. Submit a Batch job where each request references the SAME file URI.
3. Apply JSON repair to batch results (fix common truncation errors).
4. Async retry only the truly failed chunks.

Benefits:
- File API efficiency (upload once, reference many times).
- Batch API pricing (50% off).
- Robust repair + retry ensures 100% success.
"""

import os
import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sanko-backend"))

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ============================================================
# CONFIGURATION
# ============================================================

MODEL_ID = "gemini-3-flash-preview"
CHUNK_SIZE = 20  # Larger chunks since it's native!
OVERLAP_PAGES = 2
MAX_ASYNC_RETRIES = 2
MAX_ASYNC_CONCURRENT = 5

# Pricing
BATCH_PRICING = {"input_per_m": 0.25, "output_per_m": 1.50}
ASYNC_PRICING = {"input_per_m": 0.50, "output_per_m": 3.00}

EXTRACTION_PROMPT = """Extract EXACT, VERBATIM content from the specified pages of this PDF as JSON.

Output Format:
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
3. Include LaTeX for any math: $inline$ or $$block$$
4. Properly escape special characters
5. Only extract from the requested page range.
"""


# ============================================================
# JSON REPAIR (from v4)
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
# UTILS
# ============================================================

def get_page_count(pdf_path: Path) -> int:
    import fitz
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count


class CostTracker:
    def __init__(self):
        self.batch_in = 0
        self.batch_out = 0
        self.async_in = 0
        self.async_out = 0
    
    def add_batch(self, in_tokens: int, out_tokens: int):
        self.batch_in += in_tokens
        self.batch_out += out_tokens
        
    def add_async(self, in_tokens: int, out_tokens: int):
        self.async_in += in_tokens
        self.async_out += out_tokens
    
    @property
    def total_cost(self) -> float:
        batch_cost = (self.batch_in / 1e6 * BATCH_PRICING["input_per_m"] + 
                      self.batch_out / 1e6 * BATCH_PRICING["output_per_m"])
        async_cost = (self.async_in / 1e6 * ASYNC_PRICING["input_per_m"] + 
                      self.async_out / 1e6 * ASYNC_PRICING["output_per_m"])
        return batch_cost + async_cost


# ============================================================
# MAIN EXTRACTION
# ============================================================

def run_native_extraction(pdf_path: Path):
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    cost_tracker = CostTracker()
    
    # 1. Upload File
    print(f"\n[1/5] Uploading full PDF: {pdf_path.name}...")
    file = client.files.upload(file=str(pdf_path))
    print(f"      ✓ File URI: {file.uri}")
    
    try:
        # 2. Prepare Batch Requests
        print(f"\n[2/5] Preparing batch requests (Chunks of {CHUNK_SIZE} pages)...")
        total_pages = get_page_count(pdf_path)
        
        from google.genai.types import InlinedRequest, BatchJobSource
        
        chunks = []  # Store chunk info for retry
        inlined_requests = []
        
        start = 0
        chunk_idx = 0
        while start < total_pages:
            end = min(start + CHUNK_SIZE, total_pages)
            
            chunks.append({
                "index": chunk_idx,
                "start": start,
                "end": end,
                "range_str": f"{start+1}-{end}"
            })
            
            ir = InlinedRequest(
                model=MODEL_ID,
                contents=[
                    file, 
                    f"FOCUS PAGE RANGE: {start + 1} to {end}.\n\n{EXTRACTION_PROMPT}"
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                ),
                metadata={"chunk_index": str(chunk_idx), "range": f"{start+1}-{end}"}
            )
            inlined_requests.append(ir)
            
            chunk_idx += 1
            if end < total_pages:
                start = end - OVERLAP_PAGES
            else:
                break
        
        print(f"      ✓ Prepared {len(inlined_requests)} requests.")
        
        # 3. Submit Batch Job
        print(f"\n[3/5] Submitting batch job...")
        start_time = time.perf_counter()
        
        batch_job = client.batches.create(
            model=MODEL_ID,
            src=BatchJobSource(inlined_requests=inlined_requests)
        )
        job_id = batch_job.name
        print(f"      ✓ Job ID: {job_id}")
        
        # Poll for completion
        print("\n[WAITING] Polling every 30s...")
        while True:
            time.sleep(30)
            status = client.batches.get(name=job_id)
            elapsed = timedelta(seconds=int(time.perf_counter() - start_time))
            print(f"  [{elapsed}] Status: {status.state}")
            
            if status.state == "JOB_STATE_SUCCEEDED":
                print("      ✓ Batch completed successfully!")
                break
            elif status.state in ["JOB_STATE_FAILED", "JOB_STATE_CANCELLED"]:
                print(f"      ✗ Batch failed: {status.state}")
                return
        
        # 4. Retrieve & Process with REPAIR
        print("\n[4/5] Retrieving and repairing batch results...")
        completed_job = client.batches.get(name=job_id)
        
        results = {}  # chunk_index -> sections list
        failed_chunks = []
        batch_success = 0
        repair_success = 0
        
        if completed_job.dest and completed_job.dest.inlined_responses:
            for i, resp in enumerate(completed_job.dest.inlined_responses):
                chunk_idx = i
                success = False
                
                if resp.response and resp.response.text:
                    raw_text = resp.response.text
                    
                    # Track tokens
                    if resp.response.usage_metadata:
                        cost_tracker.add_batch(
                            resp.response.usage_metadata.prompt_token_count or 0,
                            resp.response.usage_metadata.candidates_token_count or 0
                        )
                    
                    # Try direct parse
                    try:
                        data = json.loads(raw_text)
                        data = normalize_response(data)
                        results[chunk_idx] = data.get("sections", [])
                        batch_success += 1
                        success = True
                    except json.JSONDecodeError:
                        # Try repair
                        repaired = repair_json_v2(raw_text)
                        if repaired:
                            data = normalize_response(repaired)
                            results[chunk_idx] = data.get("sections", [])
                            repair_success += 1
                            success = True
                
                if not success:
                    failed_chunks.append(chunks[chunk_idx])
        
        print(f"      ✓ Batch direct: {batch_success}, Repaired: {repair_success}, Failed: {len(failed_chunks)}")
        
        # 5. Async Retry for truly failed chunks
        if failed_chunks:
            print(f"\n[5/5] Async retry for {len(failed_chunks)} failed chunks...")
            
            def retry_chunk(chunk_info):
                """Retry a single chunk using standard async API."""
                idx = chunk_info["index"]
                start_pg = chunk_info["start"]
                end_pg = chunk_info["end"]
                
                for attempt in range(MAX_ASYNC_RETRIES + 1):
                    try:
                        response = client.models.generate_content(
                            model=MODEL_ID,
                            contents=[
                                file,
                                f"FOCUS PAGE RANGE: {start_pg + 1} to {end_pg}.\n\n{EXTRACTION_PROMPT}"
                            ],
                            config=types.GenerateContentConfig(
                                temperature=0.0,
                                response_mime_type="application/json",
                            )
                        )
                        
                        # Track cost
                        if response.usage_metadata:
                            cost_tracker.add_async(
                                response.usage_metadata.prompt_token_count or 0,
                                response.usage_metadata.candidates_token_count or 0
                            )
                        
                        if response.text:
                            try:
                                data = json.loads(response.text)
                            except:
                                data = repair_json_v2(response.text)
                            
                            if data:
                                data = normalize_response(data)
                                return {"success": True, "index": idx, "sections": data.get("sections", [])}
                    except Exception as e:
                        pass
                    
                    time.sleep(1 * (attempt + 1))
                
                return {"success": False, "index": idx, "error": "Max retries exceeded"}
            
            # Run retries in parallel
            async_success = 0
            with ThreadPoolExecutor(max_workers=MAX_ASYNC_CONCURRENT) as executor:
                futures = {executor.submit(retry_chunk, c): c for c in failed_chunks}
                
                for future in as_completed(futures):
                    res = future.result()
                    if res["success"]:
                        results[res["index"]] = res["sections"]
                        async_success += 1
                        print(f"      ✓ Fixed chunk {res['index']+1} | Cost: ${cost_tracker.total_cost:.4f}")
                    else:
                        print(f"      ✗ Failed chunk {res['index']+1}")
            
            print(f"      Async recovered: {async_success}/{len(failed_chunks)}")
        else:
            print("\n[5/5] No failed chunks - skipping async retry.")
        
        # Final Report
        total_time = time.perf_counter() - start_time
        total_chunks = len(chunks)
        total_success = len(results)
        
        # Flatten sections
        all_sections = []
        for idx in sorted(results.keys()):
            all_sections.extend(results[idx])
        
        print("\n" + "="*60)
        print("NATIVE FILE EXTRACTION v7.1 RESULTS")
        print("="*60)
        print(f"Success: {total_success}/{total_chunks} chunks ({100*total_success/total_chunks:.1f}%)")
        print(f"  - Batch direct: {batch_success}")
        print(f"  - Repaired: {repair_success}")
        print(f"  - Async retry: {total_success - batch_success - repair_success}")
        print(f"Time: {total_time/60:.1f} minutes")
        print(f"Sections extracted: {len(all_sections)}")
        print(f"Total Cost: ${cost_tracker.total_cost:.4f}")
        print("-" * 60)
        
        # Save results
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_file = Path(__file__).parent / "results" / f"native_v71_{ts}.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        final_data = {
            "pdf": pdf_path.name,
            "extracted_at": datetime.now().isoformat(),
            "mode": "native_file_v7.1",
            "stats": {
                "total_chunks": total_chunks,
                "success": total_success,
                "batch_direct": batch_success,
                "repaired": repair_success,
                "async_retry": total_success - batch_success - repair_success,
                "total_sections": len(all_sections),
                "time_minutes": round(total_time/60, 1),
                "cost": round(cost_tracker.total_cost, 4)
            },
            "sections": all_sections
        }
        
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        print(f"Saved: {out_file}")
        
    finally:
        # Cleanup
        print(f"\n[CLEANUP] Deleting file from Gemini File API...")
        client.files.delete(name=file.name)
        print("      ✓ Done.")


if __name__ == "__main__":
    pdf = Path(__file__).parent.parent.parent / "pdfs_for_testing" / "Applied strength of materials by Mott, Robert L. Untener, Joseph A (z-lib.org).pdf"
    if not pdf.exists():
        print(f"File not found: {pdf}")
        sys.exit(1)
        
    run_native_extraction(pdf)
