# Agent Architecture & The "Test Center" Strategy

**Status:** Finalized Blueprint  
**Date:** December 17, 2025  
**Context:** Defining the specific roles, ideal states, and evaluation metrics for the SankoSlides multi-agent system, incorporating strict Academic Verification protocols.

---

## 1. The Workflow: "The Academic Assembly Line"

We are moving away from a generic generative flow to a process-driven pipeline designed for academic rigor. Failures are isolated to specific stages.

**The Flow:**
1.  **User Input:** (Files/Topic) + (Optional: Citation Guide).
2.  **Clarifier Agent (The Negotiator):** Interacts with user to define Scope, Tone, and Style. Outputs a "Signed Contract" (Order Form).
3.  **Outliner Agent (The Architect):** Reads documents/research. Builds the structural Skeleton (Titles, Bullet points, Placeholders). User Approves here.
4.  **Planner Agent (The Librarian):** Enriches the Skeleton. Finds real citations, verifies facts, and sources specific image assets using the **VisionTool**. Output is **Strict Pydantic JSON**.
5.  **Generator Agent (The Assembler):** Maps enriched content to strict Frontend Component JSON, enforcing University Branding.
6.  **Visual QA (The Grader):** Playwright loop that visually inspects and grades the final output.

---

## 2. Agent Definitions & Evaluation Rubrics

To ensure quality, each agent has a specific Role, Ideal State, Failure Mode, and a Metric for the "Judge" to track.

### A. The Clarifier Agent ("The Negotiator")
*   **Role:** The Gatekeeper. Lives in the **Interactions API**.
*   **Goal:** Extract a valid "Order Form" without annoying the user. Must lock in **Style ID** (from `presets.json`) and **Citation Standard**.
*   **Ideal State:** Concise consultant. Detects ambiguity instantly. Refuses to proceed until the contract is clear.
*   **Failure Modes:**
    *   *The Chatty Kathy:* Asks too many questions.
    *   *The Pushover:* Accepts vague instructions ("Make it cool") without defining parameters.
    *   *The Hallucinator:* Invents styles not present in the frontend library.
*   **Judge Metric:** **"Turns to Contract"** (Lower is better).

### B. The Outliner Agent ("The Architect")
*   **Role:** Structure & Logic.
*   **Goal:** Build the logical narrative flow (Skeleton). Prioritize content mercilessly (chunking 50 pages into 10 slides).
*   **Ideal State:** Clear narrative arc (Intro -> Body -> Conclusion). Visual awareness (marks slides as "Needs Diagram" rather than dumping text).
*   **Failure Modes:**
    *   *The Wall of Text:* Overloading slides (e.g., 10+ bullet points).
    *   *The Broken Telephone:* Misses the document's core thesis.
    *   *The Orphan:* Creates empty slides with only titles.
*   **Judge Metric:** **"Information Density Score"** (Text-to-slide ratio balance).

### C. The Planner Agent ("The Librarian")
*   **Role:** Enrichment & Verification. **Model: Gemini 1.5 Pro (Reasoning).**
*   **Goal:** Fill placeholders with **Real Citations** and **Contextual Assets**.
*   **Constraint:** Must output **Strict Pydantic JSON** (Metadata only). NEVER formats the citation string itself.
*   **Tooling:**
    *   **VisionTool:** Must download and verify every image URL before citing it.
    *   **Academic Search:** Must find verifiable DOIs.
*   **Ideal State:**
    *   **Academic Rigor:** Finds verifiable sources (DOI/Link). Flags unverified claims using the "Negative Constraint" protocol ("If source not found, delete point").
    *   **Asset Match:** Confirmed by Vision Model (e.g., "This image definitely contains a neural network diagram").
*   **Failure Modes:**
    *   *The Faker:* Hallucinates citations (Critical Fail).
    *   *The Lazy Searcher:* Cites blogs instead of papers.
    *   *The Mismatch:* Irrelevant imagery (caught by VisionTool).
*   **Judge Metric:** **"Citation Validity Rate"** (% of citations with verifiable DOIs) and **"Source Authority Score"** (Academic Paper > Blog).

### D. The Generator Agent ("The Assembler")
*   **Role:** Mapping & Compliance. **Model: Gemini 1.5 Flash.**
*   **Goal:** Map the enriched Pydantic content into the strict **Component JSON Schema** for the frontend. Enforce University Profile (Logo, Colors).
*   **Ideal State:** Strict adherence to the `Style ID`. Correct wrapping of Math (`$$...$$`) and Code blocks.
*   **Failure Modes:**
    *   *The Rebel:* Ignores branding constraints (e.g., changes colors).
    *   *The Breaker:* Outputs invalid JSON.
*   **Judge Metric:** **"Schema Compliance"** (Valid JSON?) and **"Profile Adherence"** (Hex code accuracy).

---

## 3. The "Test Center" (Evaluation Strategy)

We will build a "Judge Agent" (Meta-Agent) to automate the testing of this pipeline.

**The Workflow:**
1.  **Scenario Injection:** Feed the system a controlled input (e.g., "Input: 20-page Physics PDF. Intent: 10 slides, strict IEEE").
2.  **Execution:** Run the full agent chain.
3.  **Inspection:** The Judge inspects the intermediate and final outputs against the Rubrics above.
4.  **Reporting:** Generates a **Report Card**:
    *   "Clarifier: Pass (2 turns)."
    *   "Outliner: Fail (Slide 4 has 200 words)."
    *   "Planner: Fail (Citation 3 is a broken link)."

**Strategic Value:** This allows us to "Regression Test" our prompts. If we tweak the Planner's prompt to be more creative, the Judge will tell us if its "Citation Validity" score dropped.

---

## 4. Special Handling: "Replica Mode"
*   **Challenge:** OCR fails at Math (e.g., `x^2` -> `x2`).
*   **Strategy:** **Vision-to-LaTeX**.
*   **Process:** Crop equations -> Send to specialized Vision Model prompted for "LaTeX Extraction Only" -> Send LaTeX to Node Rendering Service -> Generate SVG.

## 5. Special Handling: "Playwright Grader"
*   **Concept:** The Visual QA loop doesn't just fix; it **Grades**.
*   **User Value:** The user sees a "Visual Score" (e.g., "Visual Score: 98% - Adjusted text overflow on Slide 4"). This builds trust in the "One-Shot" promise.

## 6. Citation Rendering Strategy
*   **Mechanism:** **Hybrid Logic**.
*   **Role:**
    *   **LLM (Planner):** Finds the *Data* (Author: "Smith", Year: "2023", DOI: "...").
    *   **Code (Node Service):** Formats the *String* ("Smith et al. (2023)...") using `citation-js`.
*   **Benefit:** Zero hallucination in punctuation or style rules. Perfect IEEE/APA compliance.