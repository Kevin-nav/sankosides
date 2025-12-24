# Product Guidelines: SankoSlides

## Prose & Tone
*   **Primary Tone:** **Academic & Formal**. Content must be objective, rigorous, and sophisticated, adhering to STEM conventions (e.g., appropriate use of passive voice, precise terminology).
*   **Secondary Modes (Future):** The architecture supports switching to "Clear & Concise" (bullet-heavy, active voice) or "Educational & Explanatory" (teaching-focused) modes.
*   **Core Principle:** Clarity without compromising rigor. Avoid "fluff" or overly salesy language.

## Visual Identity & Design
*   **Hierarchy of Needs:**
    1.  **Strict Compliance (University Profiles):** The system serves as a "brand guardian," enforcing specific university guidelines (colors, logos, fonts) when a profile is active.
    2.  **General Academic Standard:** For users without a specific university profile, a "General Academic" baseline ensures readability, high contrast for projectors, and professional layouts.
    3.  **Dynamic Adaptation:** Layouts must dynamically balance compliance with content density, prioritizing space for data, equations, and citations over decoration.
*   **Feedback Loop:** Design rules will be iteratively refined based on beta testing feedback from university partners.

## Zero Hallucination & Citation Protocol
*   **Strict Verification:** The AI acts as a rigorous fact-checker.
    *   **Internet Claims:** If a claim from an external search cannot be verified, the AI must find an alternative, verifiable source or discard the claim.
    *   **Source Material Claims:** If a claim in the *provided* material is ambiguous, the AI must first exhaustively verify it is not an internal processing error. If the ambiguity persists, it must explicitly prompt the user for clarification rather than guessing.
*   **Conservative Scope (Selectable):** Users can opt for a "Conservative Mode" where the AI refuses to generate any content not explicitly found in their uploaded documents.
*   **Citation Enforcement:** **Every** major claim must be traceable. The system should ideally link claims to specific pages or sections in the source material (e.g., "[1] Source A, p. 12"), serving as a key differentiator from competitors.

## User Interaction Principles
*   **Transparency:** The user should always understand *why* the AI made a decision (e.g., "This layout was chosen to accommodate the large table on slide 4").
*   **Negotiation First:** No pixel is rendered until the intent is aligned via the Clarifier and Outliner agents.
