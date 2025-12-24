# Product Guide: SankoSlides

## Initial Concept
SankoSlides is an AI-powered presentation engine designed specifically for the rigorous demands of STEM academia. Unlike generic slide generators, it prioritizes academic compliance, deterministic rendering, and "intent alignment"—ensuring the final output matches the student's intellectual goal without the distraction of manual formatting.

## Target Audience
*   **Primary:** STEM University Students (Undergraduate & Graduate).
*   **Secondary:** Researchers and Professors requiring citation-heavy, structured presentations.
*   **Future Expansion:** Technical professionals in corporate environments.

## Core Value Proposition
1.  **Eliminating the "Formatting Tax":** Automates time-consuming tasks like citation formatting (APA/IEEE/Harvard) and layout compliance, allowing users to focus entirely on content creation.
2.  **Unblocking Creativity:** Removes "blank canvas paralysis" by letting users dump raw thoughts, notes, or papers into the system, which then structures them into a coherent narrative.
3.  **Complex Visualization:** handle the rendering of difficult STEM elements like LaTeX equations, Mermaid diagrams, and code blocks that are often painful to format manually.

## Key Features & Workflow
*   **Deep Intent Alignment:**
    *   **Synthesis Agent:** A pre-processing engine that converts uploaded PDFs into a structured "Knowledge Base" (Summary + Sections) using multimodal analysis. This ensures the Clarifier and Planner agents have access to high-fidelity text, equations, and visual descriptions without hallucinations.
    *   **Clarifier Agent:** Engages in a multi-turn dialogue to fully understand the user's source material (documents/notes) and specific focus areas before any work begins.
    *   **Outliner Agent:** Generates a structured skeleton of the presentation for user review and modification. Development proceeds *only* after the user is satisfied with the outline.
*   **Replica & Synthesis Engines:** Supports generating slides from uploaded images (Replica) or synthesizing presentations from PDFs/docs (Synthesis).
*   **Visual Loop QA:** An autonomous quality assurance pipeline that critiques and fixes slides to ensure visual polish.

## Non-Negotiable Constraints (Anti-Features)
*   **Zero Hallucination Policy:** The system must **never** invent data, citations, or facts. It is strictly grounded in the provided source material.
*   **Deterministic Rendering:** Formatting for citations and equations must be exact and compliant, avoiding the variability common in generative AI models.
