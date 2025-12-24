# Specification: Synthesis Engine Backend Integration

## 1. Overview
Implement the "Synthesis Engine" as a production component in the backend. This system uses Gemini 3 Flash to convert user-uploaded PDFs into a structured **Knowledge Base** (Summary + Sections) containing high-fidelity text, equations (LaTeX), and visual descriptions. This knowledge base serves as the ground truth for the Clarifier and Planner agents, enabling "Zero Hallucination" and scalable context management.

## 2. Requirements

### 2.1 Data Models (`app/models/schemas.py`)
*   **DocumentSection:** Represents a chunk of content with `title`, `content`, `visuals` (list), and `page_range`.
*   **KnowledgeBase:** Container for the document set, holding a `summary` and a list of `sections`.
*   **FlowState:** Updated to include a `knowledge_base: Optional[KnowledgeBase]` field.

### 2.2 Synthesis Agent (`app/crew/agents/synthesis.py`)
*   **Role:** "Multimodal Content Analyst".
*   **Model:** `gemini-3-flash-preview`.
*   **Input:** List of file paths/bytes.
*   **Output:** Structured `KnowledgeBase` object (not just a string).
*   **Logic:**
    *   Iterate through files.
    *   Send to Gemini 3 Flash with the "STEM extraction" system prompt (from POC).
    *   Parse the output into `DocumentSection` objects.
    *   Generate a high-level `summary` of the combined content.

### 2.3 Flow Integration (`app/crew/flows/slide_generation.py`)
*   **New Method:** `run_synthesis(files)`.
*   **Trigger:** Executed before `process_clarification` when `GenerationMode.SYNTHESIS` is active.
*   **State Transition:** Populates `state.knowledge_base` and moves flow to `AWAITING_CLARIFICATION`.

### 2.4 Clarifier Context (`app/crew/agents/clarifier.py`)
*   **System Prompt:** Updated to receive `knowledge_base.summary` and a list of `section.title`s.
*   **Tooling:** Give the Clarifier a `read_section(title)` tool to fetch detailed content from `state.knowledge_base` on demand.

## 3. Success Criteria
*   `FlowState` successfully persists extracted PDF content in the database.
*   `SynthesisAgent` accurately processes the `Calculus 166.pdf` test file into structured sections with LaTeX.
*   `ClarifierAgent` can "see" the document summary and ask relevant questions without being fed the entire raw text.
*   Unit tests pass for the new Agent and Schema changes.
