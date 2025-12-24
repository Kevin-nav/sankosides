# Agents Guide

Comprehensive documentation of the 7 specialized AI agents in the SankoSlides pipeline.

## Table of Contents

- [Overview](#overview)
- [Agent Pipeline](#agent-pipeline)
- [1. Clarifier Agent](#1-clarifier-agent)
- [2. Outliner Agent](#2-outliner-agent)
- [3. Planner Agent](#3-planner-agent)
- [4. Refiner Agent](#4-refiner-agent)
- [5. Generator Agent](#5-generator-agent)
- [6. Visual QA Agent](#6-visual-qa-agent)
- [7. Helper Agent](#7-helper-agent)
- [Model Selection](#model-selection)
- [Custom Agent Development](#custom-agent-development)

---

## Overview

SankoSlides uses a multi-agent architecture where each agent specializes in one task. This approach provides:

- **Separation of Concerns**: Each agent focuses on one thing
- **Quality Control**: Multiple agents verify each other's work
- **Debuggability**: Easy to identify which stage failed
- **Flexibility**: Swap agents or models without rewriting

All agents use Google Gemini 3 models via custom CrewAI integration.

---

## Agent Pipeline

```
User Input
    │
    ▼
┌─────────────┐
│  Clarifier  │ ◄── Multi-turn conversation
│  (Flash)    │     Gathers requirements
└──────┬──────┘
       │ OrderForm
       ▼
┌─────────────┐
│   Outliner  │ ◄── Creates skeleton
│   (Flash)   │     [USER REVIEW POINT]
└──────┬──────┘
       │ Skeleton
       ▼
┌─────────────┐
│   Planner   │ ◄── Writes full content
│   (Pro)     │     Adds placeholders for assets
└──────┬──────┘
       │ PlannedContent
       ▼
┌─────────────┐
│   Refiner   │ ◄── Renders LaTeX, Mermaid
│   (Pro)     │     Verifies citations
└──────┬──────┘
       │ RefinedContent
       ▼
┌─────────────┐
│  Generator  │ ◄── Creates HTML slides
│   (Flash)   │     Applies templates
└──────┬──────┘
       │ GeneratedPresentation
       ▼
┌─────────────┐
│  Visual QA  │ ◄── Grades slide quality
│   (Flash)   │     95% pass threshold
└──────┬──────┘
       │
       ▼
   Pass? ────No───► ┌─────────────┐
       │            │   Helper    │ ◄── Diagnoses failures
       │            │   (Pro)     │     Adds guardrails
      Yes           └──────┬──────┘
       │                   │
       ▼                   ▼
   Complete           Retry (max 2x)
```

---

## 1. Clarifier Agent

**File:** `app/crew/agents/clarifier.py`

**Model:** Gemini 3 Flash (fast, conversational)

**Purpose:** Gather all requirements from the user through natural conversation.

### Responsibilities

- Ask focused, single questions
- Collect presentation title, audience, slide count
- Determine focus areas and emphasis style
- Identify citation and theme preferences
- Know when to stop asking questions

### Output: `OrderForm`

```python
class OrderForm(BaseModel):
    presentation_title: str
    target_audience: str
    target_slides: int = 8
    theme_id: str = "modern"
    citation_style: str = "apa"
    key_topics: List[str]
    focus_areas: List[str]
    emphasis_style: str = "detailed"  # detailed, concise, visual-heavy
    include_speaker_notes: bool = True
    is_complete: bool = False
```

### Configuration

```python
def create_clarifier_agent() -> Agent:
    return Agent(
        role="Requirements Analyst",
        goal="Gather complete presentation requirements through conversation",
        backstory="Expert at asking the right questions to understand user needs",
        llm=CLARIFIER_LLM,  # Gemini 3 Flash
        verbose=True,
    )
```

### Best Practices

- Ask ONE question at a time
- Provide examples when asking for preferences
- Validate responses before marking complete
- Handle vague answers gracefully

---

## 2. Outliner Agent

**File:** `app/crew/agents/outliner.py`

**Model:** Gemini 3 Flash

**Purpose:** Create the presentation skeleton that the user can review and modify.

### Responsibilities

- Structure slides logically
- Determine appropriate slide types (title, content, section, etc.)
- Identify which slides need diagrams, equations, citations
- Estimate presentation duration

### Output: `Skeleton`

```python
class Skeleton(BaseModel):
    presentation_title: str
    target_audience: str
    narrative_arc: str
    slides: List[SkeletonSlide]
    estimated_duration_minutes: int

class SkeletonSlide(BaseModel):
    order: int
    title: str
    content_type: SlideContentType  # title, content, section, conclusion, etc.
    description: str
    needs_diagram: bool = False
    needs_equation: bool = False
    needs_citation: bool = False
    citation_topic: Optional[str] = None
```

### Slide Content Types

| Type | Description | Use Case |
|------|-------------|----------|
| `title` | Opening slide | First slide |
| `content` | Standard bullet points | Most slides |
| `section` | Section divider | Topic transitions |
| `two_column` | Side-by-side comparison | Pros/cons, comparisons |
| `image` | Image-focused | Visual content |
| `diagram` | Diagram-focused | Processes, architectures |
| `math` | Equation-focused | Formulas, derivations |
| `quote` | Quote highlight | Key statements |
| `conclusion` | Summary | Last slide |

---

## 3. Planner Agent

**File:** `app/crew/agents/planner.py`

**Model:** Gemini 3 Pro (high reasoning)

**Purpose:** Write the complete slide content with full detail.

### Responsibilities

- Write 3-5 substantive bullet points per slide
- Add citation queries for academic claims
- Insert equation placeholders (e.g., `{{EQUATION: linear regression}}`)
- Insert diagram placeholders (e.g., `{{DIAGRAM: neural network architecture}}`)
- Write speaker notes if requested

### Output: `PlannedContent`

```python
class PlannedContent(BaseModel):
    presentation_title: str
    target_audience: str
    theme_id: str
    citation_style: str
    slides: List[PlannedSlide]

class PlannedSlide(BaseModel):
    order: int
    title: str
    content_type: SlideContentType
    bullet_points: List[str]
    speaker_notes: Optional[str]
    citation_queries: List[str]  # Search terms for citations
    equation_placeholder: Optional[str]  # Description for LaTeX
    diagram_placeholder: Optional[str]  # Description for Mermaid
    template_type: Optional[str]  # Suggested template
```

### Placeholder Syntax

```
Bullet with citation: "Neural networks utilize backpropagation {{CITE: backpropagation algorithm}}"
Equation: "{{EQUATION: gradient descent update rule}}"
Diagram: "{{DIAGRAM: feedforward neural network with 3 layers}}"
```

---

## 4. Refiner Agent

**File:** `app/crew/agents/refiner.py`

**Model:** Gemini 3 Pro

**Purpose:** Verify content and render all assets (LaTeX, Mermaid, citations).

### Responsibilities

- Convert equation placeholders to LaTeX and render to SVG
- Convert diagram placeholders to Mermaid and render to SVG
- Search and verify academic citations
- Format citations in requested style (APA, IEEE, etc.)
- Remove unverified claims

### Tools

- **RenderServiceTool**: Calls the Render Service for LaTeX/Mermaid
- Uses `app/clients/render.py` for HTTP requests

### Output: `RefinedContent`

```python
class RefinedContent(BaseModel):
    presentation_title: str
    target_audience: str
    theme_id: str
    citation_style: str
    slides: List[RefinedSlide]
    total_citations: int
    equations_rendered: int
    diagrams_rendered: int

class RefinedSlide(BaseModel):
    order: int
    title: str
    content_type: SlideContentType
    bullet_points: List[str]
    template_type: str
    
    # Rendered assets
    equation_latex: Optional[str]
    equation_svg: Optional[str]
    diagram_mermaid: Optional[str]
    diagram_svg: Optional[str]
    
    # Citations
    citations: List[CitationMetadata]
    formatted_citations: List[str]
    
    # Images
    image_url: Optional[str]
    image_alt: Optional[str]
    image_caption: Optional[str]
```

---

## 5. Generator Agent

**File:** `app/crew/agents/generator.py`

**Model:** Gemini 3 Flash

**Purpose:** Convert refined content into semantic HTML slides.

### Responsibilities

- Select appropriate template for each slide
- Embed rendered SVGs and images
- Apply theme CSS classes
- Structure HTML semantically

### Template Selection Logic

```python
def select_template(slide: RefinedSlide) -> str:
    if slide.diagram_svg:
        return "diagram"
    if slide.equation_svg:
        return "math"
    if slide.image_url:
        return "image"
    if slide.content_type == SlideContentType.TITLE:
        return "title"
    if slide.content_type == SlideContentType.CONCLUSION:
        return "conclusion"
    return "content"
```

### Output: `GeneratedPresentation`

```python
class GeneratedPresentation(BaseModel):
    title: str
    theme_id: str
    slides: List[GeneratedSlide]
    total_slides: int

class GeneratedSlide(BaseModel):
    order: int
    title: str
    theme_id: str
    rendered_html: str  # Complete HTML for slide
    speaker_notes: Optional[str]
```

### HTML Structure

```html
<div class="slide slide-3" data-template="content">
  <div class="slide-header">
    <h1 class="slide-title">Neural Network Architecture</h1>
  </div>
  <div class="slide-content">
    <ul>
      <li>Input layer receives features</li>
      <li>Hidden layers learn representations</li>
      <li>Output layer produces predictions</li>
    </ul>
    <div class="diagram">
      <svg>...</svg>
    </div>
  </div>
</div>
```

---

## 6. Visual QA Agent

**File:** `app/crew/agents/visual_qa.py`

**Model:** Gemini 3 Flash (with vision capabilities)

**Purpose:** Grade the visual quality of generated slides.

### Responsibilities

- Render slides to images (screenshots)
- Evaluate visual quality (0-100 score)
- Check text readability
- Verify image/diagram placement
- Identify layout issues

### Grading Criteria

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Readability | 25% | Text size, contrast, spacing |
| Layout | 25% | Element positioning, balance |
| Visual Appeal | 20% | Color harmony, consistency |
| Content Density | 15% | Not too crowded or sparse |
| Accessibility | 15% | Alt text, semantic structure |

### Output: `QAReport`

```python
class QAReport(BaseModel):
    session_id: str
    slides: List[QAResult]
    average_score: float
    all_passed: bool  # All slides >= 95
    total_iterations: int

class QAResult(BaseModel):
    slide_order: int
    score: float  # 0-100
    issues: List[str]
    passed: bool  # score >= 95
    iterations: int
```

### Pass Threshold

- **95%** minimum per slide
- Up to **3 QA loops** before escalating to Helper

---

## 7. Helper Agent

**File:** `app/crew/agents/helper.py`

**Model:** Gemini 3 Pro (high reasoning for debugging)

**Purpose:** Diagnose failures and help fix them.

### Responsibilities

- Analyze error messages and failure context
- Determine if direct fix or rerun is needed
- Generate guardrail prompts for retries
- Track retry budget (max 2 per agent)
- Escalate when budget exhausted

### Failure Context

```python
class FailureContext(BaseModel):
    failing_agent: str
    failure_type: str  # validation_error, agent_error, qa_loop_exceeded
    error_message: str
    previous_attempts: int
    qa_issues: List[str]  # If from Visual QA
```

### Decision Output

```python
class HelperDecision(BaseModel):
    action: str  # direct_fix, rerun_with_guardrails, escalate
    guardrails: Optional[str]  # Added to retry prompt
    fixed_output: Optional[Any]  # If direct fix
    explanation: str
```

### Guardrail Example

```python
guardrails = """
CRITICAL: Previous attempt failed with: "Slide 3 content too long"

GUARDRAILS:
1. Limit each bullet point to 15 words maximum
2. Use 3-4 bullet points per slide, not 6+
3. Move excess content to speaker notes
"""
```

### Retry Budget

```python
class RetryBudget:
    MAX_RETRIES = 2  # Per agent
    
    def can_retry(self, agent_name: str) -> bool:
        return self.attempts.get(agent_name, 0) < self.MAX_RETRIES
```

---

## Model Selection

### Which Model for Which Agent?

| Agent | Model | Why |
|-------|-------|-----|
| Clarifier | Flash | Fast, conversational |
| Outliner | Flash | Structured output, quick |
| Planner | Pro | Deep research, reasoning |
| Refiner | Pro | Complex verification |
| Generator | Flash | Template application |
| Visual QA | Flash | Image grading |
| Helper | Pro | Debugging requires reasoning |

### Thinking Levels

```python
# Available: "none", "low", "medium", "high"

CLARIFIER_LLM = GeminiLLM(model="gemini-3-flash", thinking_level="low")
PLANNER_LLM = GeminiLLM(model="gemini-3-pro", thinking_level="high")
GENERATOR_LLM = GeminiLLM(model="gemini-3-flash", thinking_level="medium")
```

---

## Custom Agent Development

### Creating a New Agent

1. **Create agent file:**

```python
# app/crew/agents/my_agent.py

from crewai import Agent, Task
from app.clients.gemini.llm import GeminiLLM

MY_LLM = GeminiLLM(model="gemini-3-flash", thinking_level="medium")

def create_my_agent() -> Agent:
    return Agent(
        role="My Role",
        goal="What this agent achieves",
        backstory="Background that helps the agent",
        llm=MY_LLM,
        verbose=True,
    )

def create_my_task(agent: Agent, input_data: MyInput) -> Task:
    return Task(
        description=f"""Your detailed instructions...""",
        expected_output="Description of output format",
        agent=agent,
    )
```

2. **Register in flow:**

```python
# app/crew/flows/slide_generation.py

from app.crew.agents.my_agent import create_my_agent, create_my_task

async def _run_my_agent(self):
    agent = create_my_agent()
    task = create_my_task(agent, self.state.input_data)
    crew = Crew(agents=[agent], tasks=[task])
    result = crew.kickoff()
    # Process result...
```

3. **Add to pipeline sequence**

### Agent Best Practices

1. **Single Responsibility**: One agent, one task
2. **Clear Outputs**: Use Pydantic models
3. **Error Handling**: Catch and report failures
4. **Logging**: Log all agent actions
5. **Testing**: Write unit tests for each agent
