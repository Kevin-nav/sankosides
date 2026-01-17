# Gemini PDF Extraction: Optimization Strategy (v8.0)

This document outlines the architecture and optimizations used to achieve **95% cost reduction** and **100% reliability** specifically for large, technical PDF extractions.

## 1. The Cost Reduction Pillars

The transition from $12.94 to **$0.63** for an 839-page PDF was made possible by four key technical pillars:

### A. Local Semantic Chunking (vs. File API)
*   **The Problem:** The Gemini File API (v1beta/files) processes the **entire document** for every request. Sending a 470k token PDF for 47 different chunk requests results in 22 million input tokens.
*   **The Fix:** We split the PDF **locally** using `PyMuPDF` into 20-page chunks.
*   **Impact:** Reduces input tokens from 22M total to ~0.5M total (**97% reduction**).

### B. Gemini Batch API (The "Happy Path")
*   **The Strategy:** We submit all chunks as a single batch job.
*   **Economics:** Batch API offers a flat **50% discount** on all input/output tokens.
*   **Implementation:** Requests are submitted with `InlinedRequest` objects to avoid the overhead of individual network connections.

### C. Visual Fidelity Optimization (`media_resolution`)
*   **The Strategy:** Explicitly setting `media_resolution=MEDIUM`.
*   **The Math:** By default, Gemini uses 1120 tokens/page. `MEDIUM` uses ~560 tokens/page.
*   **Impact:** 50% reduction in input token costs with zero measurable loss in extraction accuracy for standard text and tables.

### D. Pydantic-Enforced Strict JSON
*   **The Strategy:** Using `response_schema` with a Pydantic model.
*   **Token Savings:** Prevents the model from adding conversational filler ("Sure! Here is the JSON...") or Markdown formatting. 
*   **Impact:** Saves ~30 output tokens per request and eliminates the cost of complex regex parsing.

---

## 2. Ensuring 100% Completeness

Cost saving is useless without accuracy. We use a three-layered "Safety Net":

| Layer | Strategy | Purpose |
| :--- | :--- | :--- |
| **Overlap** | 2-page overlap between chunks | Prevents losing sections that span across page boundaries. |
| **JSON Repair** | Local `repair_json_v2` function | Salvages truncated responses (common in large chunks) without paying for retries. |
| **Sync Retry** | Parallel sync API fallback | Truly failed chunks are retried using the standard API (full price) to guarantee completion. |

---

## 3. Benchmarks & Economics

| Document | Pages | v4 (Async) | **v8 (Optimized)** | Savings |
| :--- | :--- | :--- | :--- | :--- |
| **Full Textbook** | 839 | $12.94 | **$0.63** | 95% |
| **Small Slides** | 56 | $0.85 | **$0.05** | 94% |

---

## 4. Operational Best Practices

1.  **Cache by Hash:** Before calling any API, calculate the SHA-256 hash of the PDF. If it exists in Redis, return the results instantly ($0 cost, 0s latency).
2.  **Parallel Retries:** Always run Phase 4 (Retries) with a `ThreadPoolExecutor` (4-5 workers) to avoid 30+ minute wait times for sequential API calls.
3.  **Graceful Degradation:** Use `gemini-3-flash-preview` for both initial batch and retries to maintain high extraction quality.

---
*Documented by Kevin Nchorbuno Amisom - January 4, 2026*
