# Integration Design: Synthesis Engine with Dynamic Context Management

## 1. Architectural Overview
The Synthesis Engine will be integrated as a pre-processing stage that transforms raw PDFs into a structured **Knowledge Base**. This allows for scalable context management, ensuring agents (Clarifier, Planner) only consume the data they need.

### New Component: `SynthesisAgent`
*   **Responsibility:** Convert raw PDF uploads into a structured `KnowledgeBase` object.
*   **Input:** List of PDF file paths or binary data.
*   **Output:** `KnowledgeBase` (Summary + Sections).

## 2. Data Model Changes (`app/models/schemas.py`)

We will introduce a structured way to hold document content:

```python
class DocumentSection(BaseModel):
    """A specific section of the uploaded document."""
    title: str = Field(..., description="Section header or topic")
    content: str = Field(..., description="Full text and latex content")
    visuals: List[str] = Field(default_factory=list, description="Visual descriptions in this section")
    page_range: str = Field(default="", description="e.g., '1-3'")

class KnowledgeBase(BaseModel):
    """Structured knowledge extracted from user documents."""
    summary: str = Field(..., description="High-level overview of the entire document set")
    sections: List[DocumentSection] = Field(default_factory=list, description="Detailed content chunks")
    
    def get_section_titles(self) -> List[str]:
        return [s.title for s in self.sections]

class FlowState(BaseModel):
    # ... existing fields ...
    knowledge_base: Optional[KnowledgeBase] = Field(
        default=None, 
        description="Structured content extracted from synthesis"
    )
```

## 3. Flow Integration (`slide_generation.py`)

1.  **Start:** User uploads PDFs.
2.  **Synthesis Stage:** `SynthesisAgent` processes files -> populates `state.knowledge_base`.
3.  **Clarification Stage:**
    *   **Context Injection:** The `ClarifierAgent` is *not* given the full text. Instead, it receives:
        *   File Names
        *   `knowledge_base.summary`
        *   List of `section.title`s
    *   **Tooling:** The Clarifier is given a `read_section(section_title)` tool.
    *   **Logic:**
        *   User: "I want slides on Derivatives."
        *   Clarifier (Thinking): "I see a 'Derivatives' section. I'll read it to check for specific sub-topics."
        *   Clarifier (Tool): `read_section("Derivatives")`
        *   Clarifier (Response): "The 'Derivatives' section covers Power Rule and Chain Rule. Should we include both?"

## 4. Prompt Engineering

### `SynthesisAgent`
*   **Prompt:** Updated to output JSON matching the `KnowledgeBase` schema (Summary + List of Sections) instead of flat Markdown.

### `ClarifierAgent`
*   **System Prompt Update:**
    > "You have access to the user's uploaded documents.
    > **Summary:** {summary}
    > **Available Sections:** {section_titles}
    > Use the `read_section` tool to inspect specific details if the user asks about them or to verify focus areas. Do not guess."

## 5. Benefits
*   **Scalability:** Supports large textbooks (100+ pages) without overflowing the token window.
*   **Precision:** Agents focus on relevant chunks rather than getting lost in noise.
*   **Cost:** Reduces input tokens for the majority of turns where deep reading isn't needed.