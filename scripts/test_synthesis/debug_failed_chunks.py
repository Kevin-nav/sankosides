"""
Debug script to investigate failed chunks from v8.0 extraction.

Goals:
1. See what's in the failed chunks (content type, page ranges)
2. Try different retry strategies
3. Test Gemini 2.0 Flash Lite as a cheap repair option
"""

import os
import sys
import json
from pathlib import Path

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# Failed chunk indices from v8.0 run
FAILED_CHUNKS = [1, 8, 14, 23, 30, 38, 39, 46]  # 0-indexed

CHUNK_SIZE = 20
OVERLAP_PAGES = 2


def get_page_count(pdf_path: Path) -> int:
    import fitz
    doc = fitz.open(pdf_path)
    count = len(doc)
    doc.close()
    return count


def extract_chunk_pdf(pdf_path: Path, start_page: int, end_page: int) -> bytes:
    import fitz
    doc = fitz.open(pdf_path)
    chunk = fitz.open()
    chunk.insert_pdf(doc, from_page=start_page, to_page=end_page - 1)
    data = chunk.tobytes()
    chunk.close()
    doc.close()
    return data


def get_chunk_page_range(chunk_idx: int, total_pages: int):
    """Calculate page range for a chunk index."""
    ranges = []
    start = 0
    idx = 0
    while start < total_pages:
        end = min(start + CHUNK_SIZE, total_pages)
        ranges.append((start, end))
        if end < total_pages:
            start = end - OVERLAP_PAGES
        else:
            break
        idx += 1
    
    if chunk_idx < len(ranges):
        return ranges[chunk_idx]
    return None


def analyze_failed_chunks(pdf_path: Path):
    """Analyze what's in the failed chunks."""
    print("\n" + "="*60)
    print("ANALYZING FAILED CHUNKS")
    print("="*60)
    
    total_pages = get_page_count(pdf_path)
    
    for chunk_idx in FAILED_CHUNKS:
        page_range = get_chunk_page_range(chunk_idx, total_pages)
        if page_range:
            start, end = page_range
            print(f"\nChunk {chunk_idx+1}: Pages {start+1}-{end}")
            
            # Extract and check size
            chunk_bytes = extract_chunk_pdf(pdf_path, start, end)
            print(f"  Size: {len(chunk_bytes) / 1024:.1f} KB")


def test_simple_retry(pdf_path: Path, chunk_idx: int):
    """Test a simple synchronous retry without caching."""
    print(f"\n--- Testing simple retry for chunk {chunk_idx+1} ---")
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    total_pages = get_page_count(pdf_path)
    page_range = get_chunk_page_range(chunk_idx, total_pages)
    
    if not page_range:
        print("Invalid chunk index")
        return None
    
    start, end = page_range
    chunk_bytes = extract_chunk_pdf(pdf_path, start, end)
    
    prompt = f"""Extract content from pages {start+1}-{end}.

Return JSON with this structure:
{{"sections": [{{"title": "...", "content": "...", "visuals": [], "page_range": "..."}}]}}

Rules:
1. VERBATIM extraction only
2. Valid JSON only
3. Include all text content"""

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_bytes(data=chunk_bytes, mime_type="application/pdf"),
                prompt
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
            )
        )
        
        if response.usage_metadata:
            print(f"  Tokens: {response.usage_metadata.prompt_token_count} in, {response.usage_metadata.candidates_token_count} out")
        
        if response.text:
            # Try to parse
            try:
                data = json.loads(response.text)
                sections = data.get("sections", [])
                print(f"  ✓ SUCCESS! Got {len(sections)} sections")
                return data
            except json.JSONDecodeError as e:
                print(f"  JSON parse error: {e}")
                print(f"  Response preview: {response.text[:200]}...")
                return None
        else:
            print(f"  No response text")
            return None
            
    except Exception as e:
        print(f"  ✗ Error: {type(e).__name__}: {e}")
        return None


def test_flash_lite_repair(pdf_path: Path, chunk_idx: int):
    """Test using Gemini 2.0 Flash Lite as a cheaper repair option."""
    print(f"\n--- Testing Flash Lite for chunk {chunk_idx+1} ---")
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    total_pages = get_page_count(pdf_path)
    page_range = get_chunk_page_range(chunk_idx, total_pages)
    
    if not page_range:
        print("Invalid chunk index")
        return None
    
    start, end = page_range
    chunk_bytes = extract_chunk_pdf(pdf_path, start, end)
    
    prompt = f"""Extract ALL text content from pages {start+1}-{end}.

Return ONLY valid JSON:
{{"sections": [{{"title": "Section Title", "content": "Full text...", "visuals": [], "page_range": "{start+1}-{end}"}}]}}

Be thorough - include every paragraph."""

    try:
        # Try with gemini-2.0-flash-lite (cheaper model)
        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",  # Cheaper!
            contents=[
                types.Part.from_bytes(data=chunk_bytes, mime_type="application/pdf"),
                prompt
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
            )
        )
        
        if response.usage_metadata:
            # Flash Lite pricing: $0.10/M in, $0.40/M out
            cost = (response.usage_metadata.prompt_token_count or 0) / 1e6 * 0.10 + \
                   (response.usage_metadata.candidates_token_count or 0) / 1e6 * 0.40
            print(f"  Tokens: {response.usage_metadata.prompt_token_count} in, {response.usage_metadata.candidates_token_count} out")
            print(f"  Cost: ${cost:.4f}")
        
        if response.text:
            try:
                data = json.loads(response.text)
                sections = data.get("sections", [])
                print(f"  ✓ SUCCESS with Flash Lite! Got {len(sections)} sections")
                return data
            except json.JSONDecodeError as e:
                print(f"  JSON parse error: {e}")
                return None
        else:
            print(f"  No response text")
            return None
            
    except Exception as e:
        print(f"  ✗ Error: {type(e).__name__}: {e}")
        return None


def test_context_cache_debug(pdf_path: Path, chunk_idx: int):
    """Debug context cache creation and usage."""
    print(f"\n--- Debug context cache for chunk {chunk_idx+1} ---")
    
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    total_pages = get_page_count(pdf_path)
    page_range = get_chunk_page_range(chunk_idx, total_pages)
    
    if not page_range:
        print("Invalid chunk index")
        return
    
    start, end = page_range
    chunk_bytes = extract_chunk_pdf(pdf_path, start, end)
    
    cache = None
    try:
        # Step 1: Create cache
        print("  Creating cache...")
        cache_config = types.CreateCachedContentConfig(
            model="gemini-3-flash-preview",
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_bytes(data=chunk_bytes, mime_type="application/pdf")]
                )
            ],
            ttl="300s"
        )
        
        cache = client.caches.create(model="gemini-3-flash-preview", config=cache_config)
        print(f"  ✓ Cache created: {cache.name}")
        
        if cache.usage_metadata:
            print(f"  Cached tokens: {cache.usage_metadata.total_token_count}")
        
        # Step 2: Query cache
        print("  Querying cache...")
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[f"Extract all text from pages {start+1}-{end} as JSON with sections array."],
            config=types.GenerateContentConfig(
                cached_content=cache.name,
                temperature=0.0,
                response_mime_type="application/json",
            )
        )
        
        if response.usage_metadata:
            print(f"  Response tokens: {response.usage_metadata.prompt_token_count} in, {response.usage_metadata.candidates_token_count} out")
            if hasattr(response.usage_metadata, 'cached_content_token_count'):
                print(f"  Cached tokens used: {response.usage_metadata.cached_content_token_count}")
        
        if response.text:
            print(f"  Response preview: {response.text[:200]}...")
            
    except Exception as e:
        print(f"  ✗ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if cache:
            try:
                client.caches.delete(name=cache.name)
                print("  Cache deleted.")
            except:
                pass


if __name__ == "__main__":
    pdf = Path(__file__).parent.parent.parent / "pdfs_for_testing" / "Applied strength of materials by Mott, Robert L. Untener, Joseph A (z-lib.org).pdf"
    
    if not pdf.exists():
        print(f"File not found: {pdf}")
        sys.exit(1)
    
    # 1. Analyze what's in failed chunks
    analyze_failed_chunks(pdf)
    
    # 2. Test simple retry on first failed chunk
    test_simple_retry(pdf, FAILED_CHUNKS[0])
    
    # 3. Test Flash Lite as cheap alternative
    test_flash_lite_repair(pdf, FAILED_CHUNKS[0])
    
    # 4. Debug context cache
    test_context_cache_debug(pdf, FAILED_CHUNKS[0])
