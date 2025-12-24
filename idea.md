# Product Requirements Document (PRD)

**Project Code:** `PROJECT_SLIDE_ENGINE`
**Date:** December 17, 2025
**Version:** 1.0
**Author:** Kevin Amisom Nchorbuno (Architect)


## 1. Executive Summary

SankoSlides is a web-based "Intent-Aligned Design Engine" specifically built for University STEM students. Unlike generic design tools, it focuses on **academic compliance**, **complex technical rendering** (math/code), and a **"One-Shot" generation workflow**.

The core value proposition is the **"Visual Loop"**: The system autonomously renders, critiques, and fixes its own slides to ensure pixel-perfect 1:1 fidelity with PowerPoint before the user ever sees the result.

---

## 2. Target Audience

**Primary:** University STEM Students (Engineering, Mathematics, Computer Science).
**Secondary:** General Academic Students (Humanities, Business) requiring strict citation formats.

**User Personas:**

* **The Thesis Defender:** Needs strict adherence to departmental formatting (logos, margins, fonts).
* **The Group Lead:** Needs to synthesize disparate inputs (Word docs, PDFs) into one consistent voice.
* **The Last-Minute Crammer:** Needs rapid synthesis of reading materials into a pass-grade presentation.

And many more personas that will help us get the best possible product.
---

## 3. Technical Architecture

### 3.1 High-Level Stack

* **Frontend:** Next.js (React) + Tailwind CSS.
* **Core Component:** `SlideStage` (Fixed resolution: **1280px × 720px** @ 96DPI).


* **Backend:** Python (FastAPI).
* **AI Orchestration:** **Google Gemini Interactions API**.
* **Visual Engine:** Playwright (Headless Browser) + Gemini Vision Model.
* **Export Engine:** `dom-to-pptx` (Client-side) with server-side SVG generation for math.

### 3.2 The "Interactions API" Role

We utilize the **Google Gemini Interactions API** (released Dec 2025) to replace manual agent orchestration.

* **Stateful Memory:** The API manages the conversation history (context window) on Google's servers, reducing latency and cost.
* **Built-in Agent:** We use the `gemini-deep-research` agent for the "Deep Research" mode (Syllabus generation).
* **Multimodal Input:** Handles direct file uploads (PDFs, Images) for context analysis without external OCR tools.

---

## 4. Functional Requirements

### 4.1 Mode Selection (The 3 Engines)

The system must support three distinct generation modes based on user intent:

* **Mode A: Replica Engine (Visual Match)**
* **Input:** User uploads an image of an existing slide.
* **Logic:** Vision model maps pixels to CSS absolute positioning.
* **Success Criteria:** Exported PPTX looks 95%+ identical to the uploaded image.


* **Mode B: Synthesis Engine (Context Aware)**
* **Input:** User uploads unstructured data (PDFs, handwritten notes, Word docs).
* **Logic:** AI reads content, identifies gaps, performs micro-searches if needed, and structures content into slides.
* **Constraint:** Must support handwriting recognition for math equations.


* **Mode C: Deep Research Engine**
* **Input:** User provides a topic (e.g., "The History of Anansi").
* **Logic:** Uses `gemini-deep-research` to perform multi-step web searches, fact-checking, and syllabus creation.



### 4.2 The "Negotiation" Phase (One-Shot Protocol)

* **Requirement:** The system **must not** generate slides immediately upon the first prompt.
* **Workflow:**
1. **Intent Capture:** User defines goal.
2. **Clarification:** AI asks 1-3 strategic questions (Tone, Depth, Template).
3. **Contract Generation:** AI presents a `JSON Blueprint` (The "Contract").
4. **Approval:** User clicks "Approve" -> System executes generation.



### 4.3 University Profile System

* **Requirement:** Users can define a persistent "School Profile" to automate compliance.
* **Data Fields:**
* University Name & Department.
* Logo URL (Auto-placed on every slide).
* Brand Colors (Primary/Secondary).
* **Citation Style:** Supports custom "Twist" styles (e.g., "IEEE but with bold authors").


* **Behavior:** These settings override any generic design choices.

### 4.4 STEM Capabilities

* **Equation Rendering:**
* Input: LaTeX (`$$...$$`) or visual handwriting upload.
* Display: Rendered via KaTeX/MathJax.
* Export: Converted to **High-Res SVG** to ensure vector quality in PowerPoint.


* **Diagrams:**
* Support for **Mermaid.js** to generate flowcharts and sequence diagrams from text.



### 4.5 The "Visual Loop" (Auto-Correction)

* **Requirement:** An autonomous quality assurance loop.
* **Process:**
1. Generate HTML.
2. Capture Screenshot via Playwright.
3. Vision Model compares Screenshot vs. Intended Design.
4. If mismatch found (e.g., text overflow), AI modifies CSS.
5. Repeat until "Visual Score" > 95%.


* **UI:** Display a "Ghost Coding" effect (elements streaming in) rather than a loading spinner.

---

## 5. Non-Functional Requirements

### 5.1 Fidelity & Compliance

* **Slide Size:** Strictly **1280px × 720px**.
* **Export Format:** `.pptx` (Editable).
* **Privacy:** User uploaded files (PDFs/Handwriting) must be processed transiently and not used for model training.

### 5.2 Performance

* **Latency:**
* Negotiation Response: < 2 seconds (via Interactions API state caching).
* Deep Research Outline: < 30 seconds.
* Visual Loop (Final Render): < 2 minutes per 10 slides.



### 5.3 Usability

* **DOM Identity:** Every HTML element must have a unique `data-id` attribute to enable future "Click-to-Edit" features.

---

## 6. Future Roadmap (For Context)

* **Component Selector:** Chrome DevTools-style inspector to "prompt-edit" specific elements (e.g., "Make this image pop").
* **Speaker Notes:** AI auto-generates a script for the presentation in the PPTX notes section.

---
