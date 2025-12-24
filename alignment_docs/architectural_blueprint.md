This is the **Final Architectural Blueprint** based on our discussion, decisions, and deep research into academic AI alignment. This blueprint bridges the gap between the *PRD* (`idea.md`) and the *Developer Plan* (`workflow-plan/plan.md`), solidifying the "Hybrid" approach with strict academic guardrails.

### 1. The "Hybrid" Orchestration Core (Gap A)

We will implement a **Two-Tier Orchestration System** to balance global reasoning with local control.

*   **Tier 1: The "Brain" (Google Interactions API)**
    *   **Role:** Handles high-level reasoning, stateful conversation, and deep research.
    *   **Clarification Phase:** Uses `store=true`. The session state lives on Google's servers. We just send the user's answers. This minimizes latency and token costs during the "negotiation".
    *   **Deep Research Mode:** Uses `background=true`. We fire a "Deep Research" agent task for complex topics (e.g., "History of Anansi"). The backend polls for the result asynchronously.
    *   **Why:** Leverages Gemini's massive context and built-in "Deep Research" capabilities without us rebuilding that logic.

*   **Tier 2: The "Hands" (Local Logic / CrewAI Lite)**
    *   **Role:** Takes the structured output from Tier 1 and executes the specific "SankoSlides" logic.
    *   **Layout & Design:** Local agents map content to our specific UI components using strict Pydantic models.
    *   **The Visual Loop:** This *must* be local/hybrid. We use **Playwright** to screenshot, then send that image to **Gemini 1.5 Flash** (via API) for critique, then locally parse the fix and apply CSS updates.
    *   **Why:** We need strict control over the *DOM* and *CSS* which a remote agent can't touch directly.

### 2. The "One-Shot" Rendering Pipeline (Gap B & D)

We are committing to **Client-Side Export** with **Server-Side Asset Prep**.

*   **Step 1: The "Hard" Assets (Server-Side Microservice)**
    *   We will spin up a small **Node.js Rendering Service**.
    *   **Input:** LaTeX strings (`$$...$$`), Mermaid code, or **Raw Citation Metadata** (from Pydantic).
    *   **Action:**
        *   Math: `mathjax-node` -> SVG.
        *   Diagrams: `mermaid-cli` -> SVG.
        *   Citations: `citation-js` -> Formatted HTML string (APA/IEEE/etc). **Crucial:** AI finds the data; Code formats the string.
    *   **Output:** Returns SVGs/HTML strings to the Python Backend.

*   **Step 2: The DOM Assembly (Frontend)**
    *   Next.js receives the slide data + pre-rendered SVGs.
    *   It renders the slide on the canvas (`SlideStage`).

*   **Step 3: The Export (Client-Side)**
    *   **Tool:** `dom-to-pptx`.
    *   **Action:** Since the Math/Diagrams are now standard `<svg>` elements in the DOM (thanks to Step 1), `dom-to-pptx` can capture them accurately without complex hacks. This ensures "What You See Is What You Get."

### 3. The Visual Engine (Gap C)

*   **Generator:** **Nano Banana Pro** (Gemini 3 Pro Image).
    *   **Use Case:** Generating "Concept" images (e.g., "A visual metaphor for neural networks") and handling **University Branding**.
    *   **Feature:** We will use its **14-Image Reference Injection** to pass the University Logo and Brand Colors, asking it to generate backgrounds or assets that aesthetically match the school's theme perfectly.

### 4. Summary of Tech Stack Changes

| Component | Old Plan | **New Confirmed Plan** |
| :--- | :--- | :--- |
| **Orchestration** | CrewAI (Full Control) | **Hybrid:** Interactions API (Reasoning/Research) + Local Logic (DOM/Visual Loop) |
| **Research** | Generic Agent | **Gemini Deep Research Agent** (Async/Background Mode) |
| **Data Structure**| Unstructured Text | **Strict Pydantic Models** (Enforced Schema) |
| **Export** | Unsure | **`dom-to-pptx`** (Client-side) |
| **Math/Diagrams** | Subprocess Shell Calls | **Node.js Rendering Microservice** (Sanitizes LaTeX -> SVG) |
| **Citations** | LLM Hallucination Risk | **Hybrid:** LLM finds Metadata -> Node.js Service formats String (Deterministic) |
| **Image Gen** | "Nano Banana Pro" (Vague) | **Nano Banana Pro** (Gemini 3 Pro Image) with Reference Injection |

---

**Next Steps:**
Since we are aligned, the "Thinking" phase is complete. The next logical step (when you are ready to switch modes) would be to **begin the Scaffolding Phase** (setting up the Node service and the FastAPI backend).