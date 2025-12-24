# Integration Design: Synthesis Engine with Gemini 3 Flash

## 1. Architectural Overview
The Synthesis Engine will be integrated as a pre-processing stage in the `SlideGenerationFlow`. When a user selects `GenerationMode.SYNTHESIS`, the system will trigger the multimodal extraction before entering the Clarification phase.

### New Component: `SynthesisAgent`
A new agent located at `app/crew/agents/synthesis.py` will encapsulate the logic developed in the POC.

*   **Responsibility:** Convert raw PDF uploads into high-fidelity Markdown using Gemini 3 Flash.
*   **Input:** List of PDF file paths or binary data.
*   **Output:** Structured Markdown string (preserved in FlowState).

## 2. Data Model Changes

### `app/models/schemas.py`
Update `FlowState` to store the extracted high-fidelity content:

```python
class FlowState(BaseModel):
    # ... existing fields ...
    extracted_content: Optional[str] = Field(
        default=None, 
        description="High-fidelity Markdown extracted from source documents by SynthesisAgent"
    )
    source_visuals: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of [Visual Description: ...] identified during synthesis"
    )
```

## 3. Flow Integration (`slide_generation.py`)

### Modified Execution Path:
1.  **Start:** User uploads PDFs and starts a session.
2.  **Synthesis Stage (New):**
    *   `SynthesisAgent` runs multimodal extraction on all PDFs.
    *   Results are concatenated and stored in `state.extracted_content`.
3.  **Clarification Stage (Modified):**
    *   The `ClarifierAgent` receives `state.extracted_content` in its system prompt.
    *   Instead of asking generic questions, the Clarifier can now say: *"I've analyzed your 'Calculus 166' notes. I see complex sections on Limits and Derivatives. Which of these should we focus on for the 10 slides?"*
4.  **Planning & Generation:**
    *   The `Planner` and `Generator` agents use `state.extracted_content` as the primary source of truth, ensuring zero-hallucination compliance.

## 4. Prompt Engineering (Production)

### `SynthesisAgent` System Prompt:
Based on the successful POC prompt, refined for production JSON output if needed, or kept as Markdown for human-readability during debugging.

### `ClarifierAgent` System Prompt Update:
Add a instruction: *"You are provided with `extracted_content` from the user's documents. Use this to guide the negotiation. If the user mentions a topic not in the content, flag it as a potential hallucination risk."*

## 5. Performance & Scalability
*   **Async Processing:** Synthesis will run asynchronously.
*   **Caching:** Store extracted Markdown in the database alongside the session to avoid re-processing same files.
*   **Rate Limiting:** Implement a queue for multimodal requests to handle Gemini API limits.

## 6. Next Steps (Subject to User Approval)
1.  Implement `app/crew/agents/synthesis.py`.
2.  Update `app/models/schemas.py` with new `FlowState` fields.
3.  Integrate the `synthesis` method into `SlideGenerationFlow`.
4.  Update `Clarifier` prompts to consume the extracted content.
