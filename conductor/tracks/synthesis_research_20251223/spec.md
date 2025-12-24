# Specification: Synthesis Engine - Gemini 3 Flash Native PDF Parsing

## 1. Overview
The "Synthesis Engine" is a core component of SankoSlides responsible for converting user-uploaded documents (PDFs) into structured content for slide generation. We aim to leverage the new **Gemini 3 Flash** model's native multimodal PDF parsing capabilities to improve the extraction of text, equations, diagrams, and images compared to traditional text-only OCR methods.

## 2. Goals
*   **High-Fidelity Extraction:** Accurately extract text while preserving the context of visual elements (charts, diagrams, formulas).
*   **POC Verification:** Create a standalone script to test Gemini 3 Flash on a representative dataset of STEM PDFs.
*   **Integration Strategy:** Design a seamless integration plan for the `SynthesisAgent` in the backend, subject to user approval.

## 3. Data Sources
*   **Test Dataset:** A set of STEM PDFs located in `pdfs_for_testing/`:
    *   `Calculus 166.pdf` (Math-heavy)
    *   `Complete Lecture Notes.pdf` (Mixed content)
    *   `ENGINEERING DRAWING R3.pdf` (Visual-heavy)

## 4. Requirements
*   **Model:** Gemini 3 Flash (via Google GenAI SDK).
*   **Input:** PDF files (multimodal input).
*   **Output:** Structured JSON or Markdown containing:
    *   Section headers
    *   Body text
    *   Identified visual elements (descriptions of diagrams)
    *   LaTeX equations (preserved as text)
*   **Performance:** Must be faster and more context-aware than a pure text-based approach (e.g., PyPDF2 or standard OCR).

## 5. Success Criteria
*   POC script successfully processes all test PDFs.
*   Generated output correctly identifies and describes at least 90% of visual diagrams in the `ENGINEERING DRAWING R3.pdf` file.
*   Mathematical equations in `Calculus 166.pdf` are extracted as valid LaTeX.
*   A clear "Integration Design Document" is produced for user review.

## 6. Constraints
*   **Stop Condition:** The track must **NOT** proceed to integrate code into the main `sanko-backend` application until the user explicitly approves the findings and design.
