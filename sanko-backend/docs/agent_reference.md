# SankoSlides Agent Reference

A quick reference for all agents in the slide generation pipeline.

---

## Pipeline Overview

```
User Input → Clarifier → Outliner → Planner → Refiner → Generator → Visual QA → Helper (if needed) → Export
```

---

## 1. Clarifier Agent

**Model:** Gemini Flash  
**File:** `app/crew/agents/clarifier.py`

**Purpose:** Gather presentation requirements through conversation.

| Responsibility | Description |
|---------------|-------------|
| Extract topic | Identify what the presentation is about |
| Determine scope | How many slides, target audience, depth |
| Gather preferences | Theme, citation style, tone |
| Confirm requirements | Show summary card for user approval |

**Tools:**
| Tool | Purpose |
|------|---------|
| `ListSectionsTool` | Browse document structure |
| `ReadSectionTool` | Read specific sections from uploaded PDFs |

**Output:** `OrderForm` (topic, slide_count, audience, style preferences)

---

## 2. Outliner Agent

**Model:** Gemini Flash  
**File:** `app/crew/agents/outliner.py`

**Purpose:** Create the presentation skeleton/structure.

| Responsibility | Description |
|---------------|-------------|
| Analyze content | Use knowledge base from PDF extraction |
| Create structure | Title, narrative arc, slide titles |
| Assign templates | Which layout type for each slide |
| Mark assets | Which slides need diagrams/equations |

**Tools:**
| Tool | Purpose |
|------|---------|
| `ListSectionsTool` | Browse available content sections |
| `ReadSectionTool` | Read document content for structuring |

**Output:** `Skeleton` (slide titles, template types, narrative flow)

---

## 3. Planner Agent

**Model:** Gemini Pro  
**File:** `app/crew/agents/planner.py`

**Purpose:** Fill skeleton with detailed content.

| Responsibility | Description |
|---------------|-------------|
| Write bullet points | 3-5 key points per slide |
| Add placeholders | `[[EQUATION: ...]]`, `[[DIAGRAM: ...]]` |
| Write speaker notes | Detailed talking points |
| Research citations | Academic references for claims |

**Tools:**
| Tool | Purpose |
|------|---------|
| `ReadSectionTool` | Extract content from source documents |
| `AcademicSearchTool` | Search for academic citations (CrossRef, Semantic Scholar) |

**Output:** `PlannedContent` (slides with bullet points, placeholders)

---

## 4. Refiner Agent

**Model:** Gemini Pro  
**File:** `app/crew/agents/refiner.py`

**Purpose:** Convert placeholders to real assets.

| Responsibility | Description |
|---------------|-------------|
| Render equations | LaTeX → SVG via render service |
| Generate diagrams | Mermaid code → SVG |
| Validate citations | Check DOIs, format references |
| Process images | Search and embed relevant images |

**Tools:**
| Tool | Purpose |
|------|---------|
| `RenderServiceTool` | Render LaTeX/Mermaid to SVG |
| `AcademicSearchTool` | Validate and enrich citations |
| `ImageSearchTool` | Find relevant images (Unsplash, Pexels) |
| `ImageGenerationTool` | Generate custom images with DALL-E/Imagen |

**Output:** `RefinedContent` (slides with rendered assets)

---

## 5. Generator Agent

**Model:** Gemini Flash  
**File:** `app/crew/agents/generator.py`

**Purpose:** Generate final HTML slides.

| Responsibility | Description |
|---------------|-------------|
| Apply themes | Colors, fonts, spacing |
| Add branding | University badge, footer |
| Build HTML | Complete slide markup |
| Number slides | "1 of 10" format |

**Tools:**
| Tool | Purpose |
|------|---------|
| (None) | Uses template system directly, no external tools |

**Output:** `GeneratedPresentation` (HTML slides ready for preview)

---

## 6. Visual QA Agent

**Model:** Gemini Flash (Vision)  
**File:** `app/crew/agents/visual_qa.py`

**Purpose:** Grade slides visually and catch issues.

| Responsibility | Description |
|---------------|-------------|
| Screenshot slides | Render HTML → PNG |
| Grade quality | 5 criteria, 0-100 score |
| Identify issues | Overlaps, cutoffs, missing content |
| Trigger retries | Up to 3 attempts per slide |

**Tools:**
| Tool | Purpose |
|------|---------|
| `VisionTool` | Analyze slide screenshots with Gemini Vision |

**Grading Criteria:**
1. Layout Quality (0-20)
2. Typography (0-20)
3. Content Visibility (0-20)
4. Visual Hierarchy (0-20)
5. Completeness (0-20)

**Pass Threshold:** 95/100

---

## 7. Helper Agent

**Model:** Gemini Pro  
**File:** `app/crew/agents/helper.py`

**Purpose:** Fix failures when other agents or QA fails.

| Responsibility | Description |
|---------------|-------------|
| Analyze failures | Determine root cause |
| Route to stage | Decide which agent to re-run |
| Create guardrails | Inject constraints to prevent same errors |
| Graceful degradation | Return slides anyway if unfixable |

**Tools:**
| Tool | Purpose |
|------|---------|
| (All tools) | Has access to all tools for recovery operations |

**Stage Routing:**
| Issue Type | Target Stage |
|-----------|--------------|
| "Too much content" | Planner |
| "Equation broken" | Refiner |
| "Layout overlap" | Generator |

**Retry Budget:** 3 per stage

---

## Available Tools Summary

| Tool | File | Used By |
|------|------|---------|
| `ListSectionsTool` | `context_tool.py` | Clarifier, Outliner |
| `ReadSectionTool` | `context_tool.py` | Clarifier, Outliner, Planner |
| `AcademicSearchTool` | `academic_search_tool.py` | Planner, Refiner |
| `RenderServiceTool` | `render_service_tool.py` | Refiner |
| `ImageSearchTool` | `image_search_tool.py` | Refiner |
| `ImageGenerationTool` | `image_generation_tool.py` | Refiner |
| `VisionTool` | `vision_tool.py` | Visual QA |
| `SynthesisTool` | `synthesis_tool.py` | (PDF extraction) |

---

## Model Selection Summary

| Agent | Model | Why |
|-------|-------|-----|
| Clarifier | Flash | Fast, conversational |
| Outliner | Flash | Structured output |
| Planner | Pro | Deep research |
| Refiner | Pro | Complex verification |
| Generator | Flash | Template application |
| Visual QA | Flash + Vision | Image grading |
| Helper | Pro | Debugging requires reasoning |
