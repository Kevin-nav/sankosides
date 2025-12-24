# Specification: Synthesis Engine - Frontend Integration

## 1. Overview
Integrate the backend's Synthesis Engine into the Next.js frontend. This enables users to upload PDF documents, which are then processed by the `SynthesisAgent` (Gemini 3 Flash) to create a grounded knowledge base for the presentation generation workflow.

## 2. Requirements

### 2.1 File Upload UI (`ClarifierChat` & `ModeSelector`)
*   **UI Component:** Add a file upload area (drag & drop) visible when "Synthesis Mode" is selected.
*   **Validation:** Restrict to PDF files, max 50MB (initially).
*   **State:** Manage `file` state in `dashboard-shell` or context.

### 2.2 API Client (`lib/api-client.ts`)
*   **Update `startGeneration`:** Modify to accept an optional `files: File[]` argument.
*   **Multipart/Form-Data:** If files are present, the request must send `FormData` instead of JSON.

### 2.3 Next.js API Route (`app/api/generate/start/route.ts`)
*   **Handle Multipart:** Logic to parse `FormData`.
*   **Forward to Backend:** Send the files to the FastAPI backend's `start` endpoint (which needs to be updated to accept uploads).

### 2.4 User Experience
*   **Loading State:** Show a "Synthesizing Documents..." spinner/progress bar while the backend processes the files (this can take 10-20 seconds).
*   **Context Indicator:** Once synthesis is done, the Chat interface should indicate "Context Loaded: [File Name]" to give the user confidence.

## 3. Architecture Flow
1.  User selects "Synthesis Mode".
2.  User drops PDF.
3.  User clicks "Start".
4.  Frontend sends `POST /api/generate/start` with file.
5.  Frontend -> Backend `POST /api/generation/start` (multipart).
6.  Backend runs `SlideGenerationFlow.run_synthesis`.
7.  Backend returns `session_id`.
8.  Frontend connects SSE stream (`/api/generate/stream/[id]`).
9.  Chat begins with grounded context.

## 4. Success Criteria
*   User can upload a PDF.
*   Chat interface successfully connects to a session *after* synthesis is complete.
*   The first message from the Clarifier reflects knowledge of the uploaded document.
