"""
Async Chunked PDF Extraction Test v3.2

Features:
- Async/concurrent chunk processing (sliding window)
- REAL token tracking from API response
- LIVE running cost display  
- Graceful shutdown (Ctrl+C saves progress)
- PROGRESSIVE SAVING: saves after each chunk (resume from any point)
- Resume capability from previous runs

Models & Pricing (Dec 2025):
- gemini-3-flash-preview: $0.50/M input, $3.00/M output
- gemini-2.0-flash-lite: $0.10/M input, $0.40/M output
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
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
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
DEFAULT_CHUNK_SIZE = 8
OVERLAP_PAGES = 2
MAX_CONCURRENT_REQUESTS = 5
MAX_RETRIES = 2
RETRY_DELAY = 1.0

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
        self._original_handler = None
    
    def __enter__(self):
        self._original_handler = signal.signal(signal.SIGINT, self._handle_signal)
        return self
    
    def __exit__(self, *args):
        signal.signal(signal.SIGINT, self._original_handler)
    
    def _handle_signal(self, signum, frame):
        with self._lock:
            if self.shutdown_requested:
                print("\n\n⚠️  Force quit!")
                sys.exit(1)
            self.shutdown_requested = True
            print("\n\n⚠️  Stopping... (progress is already saved)")
            print("    Press Ctrl+C again to force quit.\n")
    
    @property
    def should_stop(self) -> bool:
        with self._lock:
            return self.shutdown_requested


# ============================================================
# PROGRESSIVE SAVE MANAGER
# ============================================================

class ProgressManager:
    """Saves progress after each chunk for resume capability."""
    
    def __init__(self, output_dir: Path, pdf_hash: str):
        self.output_dir = output_dir
        self.pdf_hash = pdf_hash[:16]
        self.progress_file = output_dir / f"progress_{self.pdf_hash}.json"
        self.sections_file = output_dir / f"sections_{self.pdf_hash}.jsonl"  # JSON Lines for append
        self._lock = threading.Lock()
        
        # Ensure output dir exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def load_progress(self) -> Dict:
        """Load existing progress if available."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, "r") as f:
                    return json.load(f)
            except:
                pass
        return {"completed_chunks": [], "tokens": {}, "costs": {}}
    
    def save_chunk(self, chunk_index: int, chunk_result: Dict):
        """Save a single chunk result immediately (append to JSONL)."""
        with self._lock:
            # Append to sections file (JSON Lines format - one JSON per line)
            with open(self.sections_file, "a", encoding="utf-8") as f:
                record = {
                    "chunk_index": chunk_index,
                    "success": chunk_result.get("success", False),
                    "sections": chunk_result.get("sections", []),
                    "tokens": chunk_result.get("tokens", {}),
                    "error": chunk_result.get("error"),
                    "timestamp": datetime.now().isoformat(),
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    def save_progress(self, completed: List[int], total_tokens: Dict, total_cost: float, 
                     total_chunks: int, successful: int, failed: int):
        """Save overall progress state."""
        with self._lock:
            progress = {
                "pdf_hash": self.pdf_hash,
                "completed_chunks": completed,
                "total_chunks": total_chunks,
                "successful": successful,
                "failed": failed,
                "tokens": total_tokens,
                "cost": f"${total_cost:.4f}",
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.progress_file, "w") as f:
                json.dump(progress, f, indent=2)
    
    def get_completed_chunks(self) -> set:
        """Get set of already completed chunk indices."""
        completed = set()
        if self.sections_file.exists():
            try:
                with open(self.sections_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            record = json.loads(line)
                            completed.add(record["chunk_index"])
            except:
                pass
        return completed
    
    def compile_final_output(self, pdf_name: str, total_pages: int) -> Dict:
        """Compile all chunks into final knowledge base."""
        all_sections = []
        chunk_records = []
        
        if self.sections_file.exists():
            with open(self.sections_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        record = json.loads(line)
                        chunk_records.append(record)
                        if record.get("success") and record.get("sections"):
                            all_sections.extend(record["sections"])
        
        # Sort by chunk index to maintain order
        chunk_records.sort(key=lambda x: x["chunk_index"])
        
        return {
            "summary": f"Extracted from {pdf_name} ({total_pages} pages)",
            "total_sections": len(all_sections),
            "sections": all_sections,
        }


# ============================================================
# PROMPTS
# ============================================================

EXTRACTION_PROMPT = """Extract EXACT, VERBATIM content from this PDF chunk as JSON.

Output format:
{{
  "sections": [
    {{
      "title": "Section header",
      "content": "VERBATIM text - do NOT summarize",
      "visuals": ["diagram descriptions"],
      "page_range": "1-3"
    }}
  ]
}}

Rules:
1. Valid JSON only - no markdown
2. Extract VERBATIM - never summarize
3. Include LaTeX: $inline$ or $$block$$
4. Escape special characters properly
"""


# ============================================================
# TOKEN TRACKING
# ============================================================

@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    candidates_tokens: int = 0
    thoughts_tokens: int = 0
    total_tokens: int = 0
    
    def add(self, other: 'TokenUsage'):
        self.prompt_tokens += other.prompt_tokens
        self.candidates_tokens += other.candidates_tokens
        self.thoughts_tokens += other.thoughts_tokens
        self.total_tokens += other.total_tokens
    
    def to_dict(self) -> Dict:
        return {
            "input": self.prompt_tokens,
            "output": self.candidates_tokens,
            "thinking": self.thoughts_tokens,
            "total": self.total_tokens,
        }


class CostTracker:
    def __init__(self):
        self.tokens = TokenUsage()
        self._lock = threading.Lock()
    
    def add(self, tokens: TokenUsage):
        with self._lock:
            self.tokens.add(tokens)
    
    @property
    def total_cost(self) -> float:
        pricing = PRICING[EXTRACTION_MODEL]
        input_cost = (self.tokens.prompt_tokens / 1_000_000) * pricing["input"]
        output_cost = ((self.tokens.candidates_tokens + self.tokens.thoughts_tokens) / 1_000_000) * pricing["output"]
        return input_cost + output_cost
    
    def to_dict(self) -> Dict:
        return self.tokens.to_dict()


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


def extract_chunk_pdf(pdf_path: Path, start_page: int, end_page: int) -> bytes:
    import fitz
    doc = fitz.open(pdf_path)
    chunk_doc = fitz.open()
    chunk_doc.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
    pdf_bytes = chunk_doc.tobytes()
    chunk_doc.close()
    doc.close()
    return pdf_bytes


def parse_token_usage(response) -> TokenUsage:
    tokens = TokenUsage()
    try:
        if hasattr(response, 'usage_metadata'):
            usage = response.usage_metadata
            tokens.prompt_tokens = getattr(usage, 'prompt_token_count', 0) or 0
            tokens.candidates_tokens = getattr(usage, 'candidates_token_count', 0) or 0
            tokens.thoughts_tokens = getattr(usage, 'thoughts_token_count', 0) or 0
            tokens.total_tokens = getattr(usage, 'total_token_count', 0) or 0
    except:
        pass
    return tokens


def repair_json(text: str) -> Optional[Dict]:
    if not text:
        return None
    
    text = re.sub(r'^```json\s*', '', text.strip())
    text = re.sub(r'\s*```$', '', text.strip())
    
    try:
        return json.loads(text)
    except:
        pass
    
    repaired = text
    if repaired.count('"') % 2 != 0:
        repaired += '"'
    
    open_braces = repaired.count('{') - repaired.count('}')
    open_brackets = repaired.count('[') - repaired.count(']')
    repaired = re.sub(r',\s*$', '', repaired)
    repaired += ']' * max(0, open_brackets)
    repaired += '}' * max(0, open_braces)
    
    try:
        return json.loads(repaired)
    except:
        pass
    
    return None


def normalize_response(data: Any) -> Dict:
    if data is None:
        return {"sections": []}
    if isinstance(data, list):
        return {"sections": data}
    if isinstance(data, dict) and "sections" not in data:
        if "title" in data and "content" in data:
            return {"sections": [data]}
    return data if isinstance(data, dict) else {"sections": []}


# ============================================================
# EXTRACTOR
# ============================================================

class ChunkedExtractor:
    def __init__(self, api_key: str):
        self.client = genai.Client(api_key=api_key)
    
    def extract_chunk(self, pdf_path: Path, chunk_index: int, 
                     start_page: int, end_page: int) -> Dict:
        """Extract a single chunk. Returns dict with success, sections, tokens, error."""
        result = {
            "chunk_index": chunk_index,
            "start_page": start_page,
            "end_page": end_page,
            "success": False,
            "sections": [],
            "tokens": {},
            "error": None,
            "time_ms": 0,
        }
        
        pdf_bytes = extract_chunk_pdf(pdf_path, start_page, end_page)
        
        for attempt in range(MAX_RETRIES + 1):
            start_time = time.perf_counter()
            
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
                
                result["time_ms"] = (time.perf_counter() - start_time) * 1000
                
                tokens = parse_token_usage(response)
                result["tokens"] = tokens.to_dict()
                
                if response.text is None:
                    raise ValueError("Empty response")
                
                try:
                    data = json.loads(response.text)
                except json.JSONDecodeError:
                    data = repair_json(response.text)
                    if data is None:
                        raise ValueError("Failed to parse JSON")
                
                data = normalize_response(data)
                result["sections"] = data.get("sections", [])
                result["success"] = True
                return result
                
            except Exception as e:
                result["time_ms"] = (time.perf_counter() - start_time) * 1000
                result["error"] = str(e)
                
                if attempt < MAX_RETRIES:
                    if any(x in str(e).lower() for x in ['connection', 'timeout', 'network', '10053', '10054', 'getaddrinfo']):
                        time.sleep(RETRY_DELAY * (attempt + 1))
                        continue
                break
        
        return result


# ============================================================
# MAIN TEST
# ============================================================

def run_extraction_test(
    pdf_path: Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap_pages: int = OVERLAP_PAGES,
    concurrency: int = MAX_CONCURRENT_REQUESTS,
    output_dir: Optional[Path] = None,
    resume: bool = True,
) -> Dict:
    """Run extraction with progressive saving and resume support."""
    
    print("=" * 70)
    print("ASYNC CHUNKED EXTRACTION v3.2 (Progressive Save)")
    print("=" * 70)
    print("✓ Progress saved after each chunk - resume anytime")
    print("✓ Press Ctrl+C to stop gracefully")
    
    # Setup
    pdf_hash = hash_pdf(pdf_path)
    total_pages = get_page_count(pdf_path)
    output_dir = output_dir or Path(__file__).parent / "results" / "progressive"
    
    progress_mgr = ProgressManager(output_dir, pdf_hash)
    cost_tracker = CostTracker()
    
    print(f"\nPDF: {pdf_path.name}")
    print(f"Size: {pdf_path.stat().st_size / (1024*1024):.2f} MB")
    print(f"Pages: {total_pages}")
    print(f"Chunk Size: {chunk_size} pages")
    print(f"Concurrency: {concurrency}")
    
    # Calculate chunks
    chunks = []
    start = 0
    while start < total_pages:
        end = min(start + chunk_size, total_pages)
        chunks.append((start, end))
        if end < total_pages:
            start = end - overlap_pages
        else:
            break
    
    total_chunks = len(chunks)
    
    # Check for resume
    already_completed = progress_mgr.get_completed_chunks() if resume else set()
    chunks_to_process = [(i, s, e) for i, (s, e) in enumerate(chunks) if i not in already_completed]
    
    if already_completed:
        print(f"\n📂 Resuming: {len(already_completed)}/{total_chunks} chunks already done")
    
    print(f"Chunks to process: {len(chunks_to_process)}")
    print(f"Output: {output_dir}")
    print("-" * 70)
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")
    
    extractor = ChunkedExtractor(api_key)
    
    print(f"\n[EXTRACTING] {len(chunks_to_process)} chunks remaining...\n")
    
    start_time = time.perf_counter()
    completed = len(already_completed)
    successful = len([i for i in already_completed])  # Assume previous were successful
    failed = 0
    was_interrupted = False
    
    with GracefulShutdown() as shutdown:
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            # Submit remaining chunks
            futures: Dict[Future, tuple] = {}
            for chunk_idx, start_page, end_page in chunks_to_process:
                future = executor.submit(
                    extractor.extract_chunk,
                    pdf_path, chunk_idx, start_page, end_page
                )
                futures[future] = (chunk_idx, start_page, end_page)
            
            # Process as they complete
            for future in as_completed(futures):
                if shutdown.should_stop:
                    for f in futures:
                        f.cancel()
                    was_interrupted = True
                    break
                
                chunk_idx, start_page, end_page = futures[future]
                
                try:
                    result = future.result()
                except Exception as e:
                    result = {
                        "chunk_index": chunk_idx,
                        "success": False,
                        "sections": [],
                        "tokens": {},
                        "error": str(e),
                    }
                
                # SAVE IMMEDIATELY
                progress_mgr.save_chunk(chunk_idx, result)
                
                completed += 1
                
                # Track costs
                if result.get("success"):
                    successful += 1
                    tokens = TokenUsage(**{
                        "prompt_tokens": result["tokens"].get("input", 0),
                        "candidates_tokens": result["tokens"].get("output", 0),
                        "thoughts_tokens": result["tokens"].get("thinking", 0),
                        "total_tokens": result["tokens"].get("total", 0),
                    })
                    cost_tracker.add(tokens)
                else:
                    failed += 1
                
                # Save progress state
                progress_mgr.save_progress(
                    list(already_completed | {i for i, _, _ in chunks_to_process[:completed - len(already_completed)]}),
                    cost_tracker.to_dict(),
                    cost_tracker.total_cost,
                    total_chunks, successful, failed
                )
                
                # Print status with live cost
                elapsed = time.perf_counter() - start_time
                remaining = len(chunks_to_process) - (completed - len(already_completed))
                eta = (elapsed / max(1, completed - len(already_completed))) * remaining
                
                status = "✓" if result.get("success") else "✗"
                sections = len(result.get("sections", []))
                tokens_in = result.get("tokens", {}).get("input", 0)
                tokens_out = result.get("tokens", {}).get("output", 0)
                running_cost = cost_tracker.total_cost
                
                if result.get("success"):
                    print(f"  [{completed:3d}/{total_chunks}] Chunk {chunk_idx+1:3d} {status} "
                          f"({sections:2d} sec, in:{tokens_in:,} out:{tokens_out:,}) "
                          f"💰 ${running_cost:.4f} [ETA: {timedelta(seconds=int(eta))}]")
                else:
                    error = (result.get("error", "")[:35] + "...") if result.get("error") else "?"
                    print(f"  [{completed:3d}/{total_chunks}] Chunk {chunk_idx+1:3d} {status} "
                          f"FAILED: {error} 💰 ${running_cost:.4f}")
    
    total_time = time.perf_counter() - start_time
    
    # Final summary
    print("\n" + "=" * 70)
    print("RESULTS" + (" (INTERRUPTED)" if was_interrupted else ""))
    print("=" * 70)
    print(f"Completed: {completed}/{total_chunks} chunks")
    print(f"Success Rate: {successful}/{completed} ({successful/max(1,completed)*100:.1f}%)")
    print(f"Time: {total_time:.1f}s ({total_time/60:.1f} min)")
    
    print("\n--- COSTS ---")
    print(f"TOTAL: ${cost_tracker.total_cost:.4f}")
    
    if cost_tracker.total_cost > 0 and successful > 0:
        cost_per_page = cost_tracker.total_cost / (successful * chunk_size)
        print(f"Est. cost per page: ${cost_per_page:.6f}")
    
    # Compile final knowledge base
    if completed == total_chunks and not was_interrupted:
        print("\n📦 Compiling final knowledge base...")
        kb = progress_mgr.compile_final_output(pdf_path.name, total_pages)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        kb_file = output_dir / f"knowledge_base_{timestamp}.json"
        with open(kb_file, "w", encoding="utf-8") as f:
            json.dump(kb, f, indent=2, ensure_ascii=False)
        print(f"✅ Saved: {kb_file}")
        print(f"   {kb['total_sections']} sections extracted")
    else:
        print(f"\n📂 Progress saved to: {output_dir}")
        print("   Run again to resume from where you left off")
    
    print("=" * 70)
    
    return {
        "completed": completed,
        "total": total_chunks,
        "successful": successful,
        "failed": failed,
        "cost": cost_tracker.total_cost,
        "interrupted": was_interrupted,
    }


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Async PDF extraction v3.2")
    parser.add_argument("pdf_path", nargs="?", help="Path to PDF")
    parser.add_argument("--chunk-size", type=int, default=8, help="Pages per chunk")
    parser.add_argument("--overlap", type=int, default=2, help="Overlap pages")
    parser.add_argument("--concurrency", type=int, default=5, help="Parallel requests")
    parser.add_argument("--output-dir", type=str, help="Output directory")
    parser.add_argument("--fresh", action="store_true", help="Start fresh, don't resume")
    
    args = parser.parse_args()
    
    if args.pdf_path:
        pdf_path = Path(args.pdf_path)
    else:
        pdf_path = Path(__file__).parent.parent.parent / "pdfs_for_testing" / "Applied strength of materials by Mott, Robert L. Untener, Joseph A (z-lib.org).pdf"
    
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        sys.exit(1)
    
    output_dir = Path(args.output_dir) if args.output_dir else Path(__file__).parent / "results" / "progressive"
    
    run_extraction_test(
        pdf_path=pdf_path,
        chunk_size=args.chunk_size,
        overlap_pages=args.overlap,
        concurrency=args.concurrency,
        output_dir=output_dir,
        resume=not args.fresh,
    )
