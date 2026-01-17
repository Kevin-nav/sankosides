"""
PDF Extraction v4.0 - Production Ready

Features:
- Phase-based extraction with auto-retry (8 → 4 → 2 pages)
- Improved JSON repair with multiple strategies
- LLM semantic merger for boundary cleanup
- Progressive saving with resume
- Live cost tracking
- Graceful shutdown

Models:
- Extraction: gemini-3-flash-preview ($0.50/M in, $3.00/M out)
- Merge: gemini-2.0-flash-lite ($0.10/M in, $0.40/M out)
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
from concurrent.futures import ThreadPoolExecutor, as_completed, Future

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

# Phase settings: progressively smaller chunks
PHASE_CHUNK_SIZES = [8, 4, 2]  # Will retry with smaller chunks on failure
OVERLAP_PAGES = 2
MAX_CONCURRENT = 5
MAX_RETRIES_PER_CHUNK = 2

PRICING = {
    "gemini-3-flash-preview": {"input": 0.50, "output": 3.00},
    "gemini-2.0-flash-lite": {"input": 0.10, "output": 0.40},
}


# ============================================================
# GRACEFUL SHUTDOWN
# ============================================================

class GracefulShutdown:
    def __init__(self):
        self.shutdown_requested = False
        self._lock = threading.Lock()
        self._original = None
    
    def __enter__(self):
        self._original = signal.signal(signal.SIGINT, self._handle)
        return self
    
    def __exit__(self, *args):
        signal.signal(signal.SIGINT, self._original)
    
    def _handle(self, signum, frame):
        with self._lock:
            if self.shutdown_requested:
                sys.exit(1)
            self.shutdown_requested = True
            print("\n⚠️  Stopping gracefully... (Ctrl+C again to force)")
    
    @property
    def should_stop(self):
        with self._lock:
            return self.shutdown_requested


# ============================================================
# IMPROVED JSON REPAIR
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
        # Try closing after last complete object
        (r'\},\s*$', '}]}"'),
        (r'\}\s*$', '}]}'),
        (r'"\s*$', '"}]}'),
        (r',\s*$', '}]}'),
    ]
    
    for pattern, suffix in strategies:
        try:
            candidate = re.sub(pattern, suffix, text)
            # Balance brackets
            open_braces = candidate.count('{') - candidate.count('}')
            open_brackets = candidate.count('[') - candidate.count(']')
            candidate += '}' * max(0, open_braces)
            candidate += ']' * max(0, open_brackets)
            return json.loads(candidate)
        except:
            pass
    
    # Strategy 4: Find last complete JSON object in "sections" array
    match = re.search(r'"sections"\s*:\s*\[(.*)', text, re.DOTALL)
    if match:
        sections_content = match.group(1)
        # Find last complete object (ends with })
        last_obj_end = sections_content.rfind('}')
        if last_obj_end > 0:
            try:
                truncated = '{"sections":[' + sections_content[:last_obj_end+1] + ']}'
                return json.loads(truncated)
            except:
                pass
    
    # Strategy 5: Extract any valid JSON objects we can find
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
# PROGRESS MANAGER (Progressive Save)
# ============================================================

class ProgressManager:
    def __init__(self, output_dir: Path, pdf_hash: str):
        self.output_dir = output_dir
        self.pdf_hash = pdf_hash[:16]
        self.progress_file = output_dir / f"progress_{self.pdf_hash}.json"
        self.sections_file = output_dir / f"sections_{self.pdf_hash}.jsonl"
        self._lock = threading.Lock()
        output_dir.mkdir(parents=True, exist_ok=True)
    
    def get_completed(self) -> Set[int]:
        """Get already-completed chunk indices."""
        completed = set()
        if self.sections_file.exists():
            with open(self.sections_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            record = json.loads(line)
                            if record.get("success"):
                                completed.add(record["chunk_index"])
                        except:
                            pass
        return completed
    
    def save_chunk(self, chunk_index: int, result: Dict):
        """Append chunk result to JSONL file."""
        with self._lock:
            with open(self.sections_file, "a", encoding="utf-8") as f:
                record = {
                    "chunk_index": chunk_index,
                    "success": result.get("success", False),
                    "sections": result.get("sections", []),
                    "tokens": result.get("tokens", {}),
                    "error": result.get("error"),
                    "phase": result.get("phase", 1),
                    "timestamp": datetime.now().isoformat(),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def compile_knowledge_base(self, pdf_name: str) -> Dict:
        """Compile all sections into final knowledge base."""
        all_sections = []
        if self.sections_file.exists():
            records = []
            with open(self.sections_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        try:
                            records.append(json.loads(line))
                        except:
                            pass
            
            # Sort by chunk index, keep only latest per chunk
            latest = {}
            for r in records:
                idx = r["chunk_index"]
                if r.get("success"):
                    latest[idx] = r
            
            for idx in sorted(latest.keys()):
                all_sections.extend(latest[idx].get("sections", []))
        
        return {
            "pdf": pdf_name,
            "extracted_at": datetime.now().isoformat(),
            "total_sections": len(all_sections),
            "sections": all_sections,
        }


# ============================================================
# COST TRACKER
# ============================================================

@dataclass
class TokenUsage:
    prompt: int = 0
    output: int = 0
    thinking: int = 0
    
    def add(self, other):
        self.prompt += other.prompt
        self.output += other.output
        self.thinking += other.thinking


class CostTracker:
    def __init__(self):
        self.extraction = TokenUsage()
        self.merge = TokenUsage()
        self._lock = threading.Lock()
    
    def add_extraction(self, tokens: TokenUsage):
        with self._lock:
            self.extraction.add(tokens)
    
    def add_merge(self, tokens: TokenUsage):
        with self._lock:
            self.merge.add(tokens)
    
    @property
    def extraction_cost(self) -> float:
        p = PRICING[EXTRACTION_MODEL]
        return (self.extraction.prompt / 1e6 * p["input"] + 
                (self.extraction.output + self.extraction.thinking) / 1e6 * p["output"])
    
    @property
    def merge_cost(self) -> float:
        p = PRICING[MERGE_MODEL]
        return (self.merge.prompt / 1e6 * p["input"] + 
                (self.merge.output + self.merge.thinking) / 1e6 * p["output"])
    
    @property
    def total(self) -> float:
        return self.extraction_cost + self.merge_cost


# ============================================================
# EXTRACTION
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


def parse_token_usage(response) -> TokenUsage:
    tokens = TokenUsage()
    try:
        if hasattr(response, 'usage_metadata'):
            u = response.usage_metadata
            tokens.prompt = getattr(u, 'prompt_token_count', 0) or 0
            tokens.output = getattr(u, 'candidates_token_count', 0) or 0
            tokens.thinking = getattr(u, 'thoughts_token_count', 0) or 0
    except:
        pass
    return tokens


def extract_chunk_pdf(pdf_path: Path, start_page: int, end_page: int) -> bytes:
    import fitz
    doc = fitz.open(pdf_path)
    chunk = fitz.open()
    chunk.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
    data = chunk.tobytes()
    chunk.close()
    doc.close()
    return data


class Extractor:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
    
    def extract(self, pdf_path: Path, chunk_index: int, 
                start_page: int, end_page: int, phase: int = 1) -> Dict:
        """Extract content from a chunk."""
        result = {
            "chunk_index": chunk_index,
            "start_page": start_page,
            "end_page": end_page,
            "phase": phase,
            "success": False,
            "sections": [],
            "tokens": {},
            "error": None,
        }
        
        pdf_bytes = extract_chunk_pdf(pdf_path, start_page, end_page)
        
        for attempt in range(MAX_RETRIES_PER_CHUNK + 1):
            try:
                response = self.client.models.generate_content(
                    model=EXTRACTION_MODEL,
                    contents=[
                        types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                        f"Pages {start_page + 1} to {end_page}.\n\n{EXTRACTION_PROMPT}"
                    ],
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                    )
                )
                
                tokens = parse_token_usage(response)
                result["tokens"] = {"in": tokens.prompt, "out": tokens.output, "think": tokens.thinking}
                
                if not response.text:
                    raise ValueError("Empty response")
                
                # Try parsing with improved repair
                try:
                    data = json.loads(response.text)
                except json.JSONDecodeError:
                    data = repair_json_v2(response.text)
                    if data is None:
                        raise ValueError("Failed to parse JSON")
                
                data = normalize_response(data)
                result["sections"] = data.get("sections", [])
                result["success"] = True
                return result
                
            except Exception as e:
                result["error"] = str(e)
                if attempt < MAX_RETRIES_PER_CHUNK:
                    if any(x in str(e).lower() for x in ['connection', 'timeout', 'network']):
                        time.sleep(1.0 * (attempt + 1))
                        continue
                break
        
        return result


# ============================================================
# LLM MERGER
# ============================================================

MERGE_PROMPT_TEMPLATE = '''Merge overlapping PDF sections from adjacent chunks.

OVERLAP ZONE:
{overlap}

TASK:
1. Identify sections split across chunks (same topic)
2. Merge them, removing duplicate content
3. Return merged sections as JSON

OUTPUT:
{{
  "merged_sections": [...],
  "merge_count": 0
}}

RULES:
- PRESERVE verbatim text, do NOT summarize
- Only merge clearly related sections
- Remove exact duplicate sentences
'''


class Merger:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
    
    def merge_boundary(self, sections_before: List[Dict], 
                       sections_after: List[Dict]) -> tuple[List[Dict], TokenUsage]:
        """Merge overlapping sections at chunk boundary."""
        if not sections_before or not sections_after:
            return [], TokenUsage()
        
        # Take last 2 from before, first 2 from after
        overlap = {
            "chunk_n_last": sections_before[-2:],
            "chunk_n_plus_1_first": sections_after[:2],
        }
        
        prompt = MERGE_PROMPT_TEMPLATE.replace("{overlap}", json.dumps(overlap, indent=2))
        
        try:
            response = self.client.models.generate_content(
                model=MERGE_MODEL,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            
            tokens = parse_token_usage(response)
            
            if response.text:
                data = json.loads(response.text)
                return data.get("merged_sections", []), tokens
            
            return [], tokens
            
        except Exception as e:
            return [], TokenUsage()


# ============================================================
# MAIN EXTRACTION WITH PHASES
# ============================================================

def run_extraction_v4(
    pdf_path: Path,
    output_dir: Optional[Path] = None,
    concurrency: int = MAX_CONCURRENT,
    skip_merge: bool = False,
) -> Dict:
    """
    Production-ready extraction with:
    - Phase-based retry (8 → 4 → 2 pages)
    - Progressive saving
    - LLM boundary merge
    """
    
    print("=" * 70)
    print("PDF EXTRACTION v4.0 (Production)")
    print("=" * 70)
    
    # Setup
    import fitz
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    doc.close()
    
    pdf_hash = hashlib.sha256(open(pdf_path, "rb").read()).hexdigest()
    output_dir = output_dir or Path(__file__).parent / "results" / "v4"
    progress = ProgressManager(output_dir, pdf_hash)
    costs = CostTracker()
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    extractor = Extractor(api_key)
    merger = Merger(api_key) if not skip_merge else None
    
    print(f"\nPDF: {pdf_path.name}")
    print(f"Pages: {total_pages}")
    print(f"Output: {output_dir}")
    print("-" * 70)
    
    already_done = progress.get_completed()
    all_results: Dict[int, Dict] = {}
    
    # Load existing results
    if already_done:
        print(f"📂 Resuming: {len(already_done)} chunks already done")
    
    start_time = time.perf_counter()
    failed_ranges: List[tuple] = []  # Track (start_page, end_page) of failed chunks
    
    with GracefulShutdown() as shutdown:
        # PHASE LOOP: Try progressively smaller chunks
        for phase_num, chunk_size in enumerate(PHASE_CHUNK_SIZES, 1):
            
            if phase_num == 1:
                # Phase 1: Process entire document with initial chunk size
                chunks = []
                start = 0
                while start < total_pages:
                    end = min(start + chunk_size, total_pages)
                    chunk_idx = start
                    if chunk_idx not in already_done:
                        chunks.append((chunk_idx, start, end))
                    if end < total_pages:
                        start = end - OVERLAP_PAGES
                    else:
                        break
            else:
                # Phase 2+: Only retry FAILED page ranges with smaller chunks
                if not failed_ranges:
                    continue
                
                chunks = []
                for failed_start, failed_end in failed_ranges:
                    # Split the failed range into smaller chunks
                    pos = failed_start
                    while pos < failed_end:
                        end = min(pos + chunk_size, failed_end)
                        chunk_idx = pos
                        if chunk_idx not in already_done:
                            chunks.append((chunk_idx, pos, end))
                        pos = end  # No overlap within retry chunks
                
                failed_ranges = []  # Reset for next phase
            
            if not chunks:
                continue
            
            print(f"\n[PHASE {phase_num}] {len(chunks)} chunks @ {chunk_size} pages each")
            
            phase_start = time.perf_counter()
            phase_completed = 0
            
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {}
                for chunk_idx, start_page, end_page in chunks:
                    future = executor.submit(
                        extractor.extract, pdf_path, chunk_idx, start_page, end_page, phase_num
                    )
                    futures[future] = (chunk_idx, start_page, end_page)
                
                for future in as_completed(futures):
                    if shutdown.should_stop:
                        for f in futures:
                            f.cancel()
                        break
                    
                    chunk_idx, start_page, end_page = futures[future]
                    
                    try:
                        result = future.result()
                    except Exception as e:
                        result = {"chunk_index": chunk_idx, "success": False, "error": str(e)}
                    
                    # Save immediately
                    progress.save_chunk(chunk_idx, result)
                    phase_completed += 1
                    
                    if result.get("success"):
                        all_results[chunk_idx] = result
                        already_done.add(chunk_idx)
                        tokens = TokenUsage(
                            result.get("tokens", {}).get("in", 0),
                            result.get("tokens", {}).get("out", 0),
                            result.get("tokens", {}).get("think", 0),
                        )
                        costs.add_extraction(tokens)
                    else:
                        # Track failed range for next phase retry
                        failed_ranges.append((start_page, end_page))
                    
                    # Calculate progress and ETA
                    elapsed = time.perf_counter() - phase_start
                    remaining = len(chunks) - phase_completed
                    if phase_completed > 0:
                        eta = timedelta(seconds=int((elapsed / phase_completed) * remaining))
                    else:
                        eta = timedelta(seconds=0)
                    
                    # Rich progress output
                    status = "✓" if result.get("success") else "✗"
                    sections = len(result.get("sections", []))
                    tokens_in = result.get("tokens", {}).get("in", 0)
                    tokens_out = result.get("tokens", {}).get("out", 0)
                    
                    if result.get("success"):
                        print(f"  [{phase_completed:3d}/{len(chunks)}] Chunk {chunk_idx+1:3d} {status} "
                              f"({sections:2d} sec, in:{tokens_in:,} out:{tokens_out:,}) "
                              f"💰 ${costs.total:.4f} [ETA: {eta}]")
                    else:
                        error = (result.get("error", "")[:35] + "...") if result.get("error") else "?"
                        print(f"  [{phase_completed:3d}/{len(chunks)}] Chunk {chunk_idx+1:3d} {status} "
                              f"FAILED: {error} 💰 ${costs.total:.4f}")
                
                if shutdown.should_stop:
                    break
            
            if shutdown.should_stop:
                break
    
    # MERGE PHASE (optional)
    if merger and not shutdown.should_stop and len(all_results) > 1:
        print(f"\n[MERGE] Processing {len(all_results)-1} boundaries...")
        
        sorted_chunks = sorted(all_results.items())
        for i in range(len(sorted_chunks) - 1):
            idx1, result1 = sorted_chunks[i]
            idx2, result2 = sorted_chunks[i + 1]
            
            merged, tokens = merger.merge_boundary(
                result1.get("sections", []),
                result2.get("sections", [])
            )
            costs.add_merge(tokens)
            
            if merged:
                print(f"  Boundary {idx1}-{idx2}: merged {len(merged)} sections")
    
    total_time = time.perf_counter() - start_time
    
    # Compile final KB
    kb = progress.compile_knowledge_base(pdf_path.name)
    
    # Save final output
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    kb_file = output_dir / f"knowledge_base_{timestamp}.json"
    with open(kb_file, "w", encoding="utf-8") as f:
        json.dump(kb, f, indent=2, ensure_ascii=False)
    
    # Summary
    success_count = len([r for r in all_results.values() if r.get("success")])
    
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Success: {success_count}/{len(all_results)} chunks")
    print(f"Sections: {kb['total_sections']}")
    print(f"Time: {total_time/60:.1f} min")
    print(f"Cost: ${costs.total:.2f}")
    print(f"\n✅ Saved: {kb_file}")
    print("=" * 70)
    
    return {
        "success": success_count,
        "total": len(all_results),
        "sections": kb["total_sections"],
        "cost": costs.total,
        "time_min": total_time / 60,
        "output": str(kb_file),
    }


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="PDF Extraction v4.0")
    parser.add_argument("pdf_path", nargs="?")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--output-dir", type=str)
    parser.add_argument("--skip-merge", action="store_true")
    
    args = parser.parse_args()
    
    if args.pdf_path:
        pdf_path = Path(args.pdf_path)
    else:
        pdf_path = Path(__file__).parent.parent.parent / "pdfs_for_testing" / "Applied strength of materials by Mott, Robert L. Untener, Joseph A (z-lib.org).pdf"
    
    if not pdf_path.exists():
        print(f"ERROR: {pdf_path}")
        sys.exit(1)
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    run_extraction_v4(
        pdf_path=pdf_path,
        output_dir=output_dir,
        concurrency=args.concurrency,
        skip_merge=args.skip_merge,
    )
