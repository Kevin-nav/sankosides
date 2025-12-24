# Plan: Synthesis Engine Research & POC

## Phase 1: Environment & Setup [checkpoint: fc6a1f8]
- [x] Task: Create a dedicated research directory `research/synthesis_poc` and initialize a separate virtual environment or requirements file for the POC script to avoid polluting the main backend yet. (1fb5eca)
- [x] Task: Verify API access to Gemini 3 Flash. Create a simple "Hello World" script `research/synthesis_poc/test_access.py` to confirm the model is accessible and accepts multimodal input. (e137a2d)
- [x] Task: Conductor - User Manual Verification 'Environment & Setup' (Protocol in workflow.md) (fc6a1f8)

## Phase 2: Proof of Concept Implementation [checkpoint: c3b8448]
- [x] Task: Create `research/synthesis_poc/pdf_processor.py`. Implement a function to upload a PDF file to the Gemini API (using the File API if necessary) and prompt Gemini 3 Flash to extract content. (cda265e)
- [x] Task: Run the POC script on `pdfs_for_testing/Calculus 166.pdf` and save the output to `research/synthesis_poc/results/calculus_output.md`. (cda265e)
- [x] Task: Run the POC script on `pdfs_for_testing/ENGINEERING DRAWING R3.pdf` and save the output to `research/synthesis_poc/results/drawing_output.md`. (cda265e)
- [x] Task: Run the POC script on `pdfs_for_testing/Complete Lecture Notes.pdf` and save the output to `research/synthesis_poc/results/notes_output.md`. (cda265e)
- [x] Task: Conductor - User Manual Verification 'Proof of Concept Implementation' (Protocol in workflow.md) (c3b8448)

## Phase 3: Analysis & Design
- [x] Task: Analyze the results. Compare the output against the original PDFs manually. Create a findings report `research/synthesis_poc/FINDINGS.md` documenting:
    *   Quality of equation extraction (LaTeX accuracy).
    *   Quality of diagram descriptions.
    *   Speed/Latency observations. (5596889)
- [x] Task: Draft the **Integration Design Document** at `research/synthesis_poc/INTEGRATION_DESIGN.md`.
    *   Detail how `SynthesisAgent` in `sanko-backend` will be updated.
    *   Define the data model changes (if any) to store the rich multimodal data.
    *   Propose the prompt structure for the production agent. (b27d105)
- [x] Task: **CRITICAL STOP:** Present the `FINDINGS.md` and `INTEGRATION_DESIGN.md` to the user.
    *   *Instruction:* Do not proceed to implementation. Ask the user for feedback and approval to move to the next phase (which will be a separate track or added tasks). (d6ab0fd)
- [ ] Task: Conductor - User Manual Verification 'Analysis & Design' (Protocol in workflow.md)
