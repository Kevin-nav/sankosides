# Frontend Integration Guide

This document describes the API responses, data structures, and frontend responsibilities for integrating with the SankoSlides backend.

---

## API Endpoints

### Session Flow

```
POST /api/generate/start      → Create session, get first clarification question
POST /api/generate/clarify    → Answer questions until blueprint ready
POST /api/generate/blueprint  → Get skeleton for user review
POST /api/generate/approve    → Start generation (background job)
GET  /api/generate/status/:id → Poll for generation progress
GET  /api/themes              → Get available themes
```

### Metrics & Testing Environment (Development Only)

Available when `EXPOSE_METRICS=true` (default in dev, set to `false` in production).

```
GET  /api/metrics              → All metrics with full prompts/outputs
GET  /api/metrics/summary      → Summary only (no raw data)
GET  /api/metrics/calls        → Per-call data (paginated)
GET  /api/metrics/calls/{idx}  → Single call by index
GET  /api/metrics/calls/agent/{name} → Filter by agent name
GET  /api/metrics/pricing      → Model pricing info
POST /api/metrics/reset        → Reset metrics (dev only)
```

#### Per-Call Data Structure

```json
{
  "agent_name": "planner",
  "model": "gemini-3-flash-preview",
  "thinking_level": "high",
  "timestamp": "2025-12-19T00:30:00Z",
  "duration_ms": 2500,
  "tokens": {
    "input": 1500,
    "output": 800,
    "thinking": 2000,
    "cached": 0,
    "total": 4300
  },
  "cost_usd": 0.0025,
  "success": true,
  "validation_score": 1.0,
  "raw": {
    "prompt": "Full system prompt + user input sent to model...",
    "output": "Full model response text...",
    "thinking": "Model's internal reasoning (thinking tokens)..."
  }
}
```

#### Metrics Summary Structure

```json
{
  "summary": {
    "total_agents": 5,
    "successful_agents": 5,
    "failed_agents": 0,
    "total_input_tokens": 8500,
    "total_output_tokens": 4200,
    "total_thinking_tokens": 12000,
    "total_tokens": 24700,
    "total_duration_ms": 15000,
    "average_duration_ms": 3000,
    "total_cost_usd": 0.0145,
    "agents": {
      "planner": {
        "model": "gemini-3-flash-preview",
        "thinking_level": "high",
        "executions": 1,
        "total_tokens": 4300,
        "total_thinking_tokens": 2000,
        "total_duration_ms": 2500,
        "total_cost_usd": 0.0025,
        "success_rate": 1.0
      }
    }
  },
  "calls": [...],
  "call_count": 5
}
```

#### Agents Currently Tracked

| Agent | Model | Thinking | Purpose |
|-------|-------|----------|---------|
| `clarifier_start` | Flash | None | Start session, first question |
| `clarifier_continue` | Flash | None | Follow-up clarification |
| `clarifier_blueprint` | Pro | None | Generate slide blueprint |
| `planner` | Flash | High | Enrich skeleton with citations/images |
| `generator` | **Pro** | High | Generate HTML slides |

> **Note:** Clarifier agents use the Interactions API (stateful sessions) which doesn't support thinking mode.
> Planner/Generator use `generate_content` API with full thinking mode.

#### Environment Variables

```env
# Development (default)
DEV_MODE=true
EXPOSE_METRICS=true

# Production
DEV_MODE=false
EXPOSE_METRICS=false
```

---

## Stage 1: Clarification (Clarifier Agent)

**Endpoint:** `POST /api/generate/clarify`

**Response:**
```json
{
  "session_id": "uuid",
  "interaction_id": "gemini-session-id",
  "status": "clarifying",
  "clarification_question": "What citation style do you prefer: APA, IEEE, or Harvard?",
  "questions_asked": 2,
  "order_form_complete": false
}
```

**Frontend must:**
- Display `clarification_question` to user
- Collect user's answer and send back
- Continue until `order_form_complete: true`

**Final OrderForm structure:**
```json
{
  "theme_id": "modern",
  "color_overrides": {
    "primary": "#0056A0",
    "secondary": "#FFD700",
    "accent": "#00C853",
    "background": "#FFFFFF",
    "text_primary": "#1A1A1A"
  },
  "citation_style": "apa",
  "tone": "academic",
  "target_audience": "Graduate Students",
  "target_slides": 8,
  "presentation_title": "Introduction to Neural Networks",
  "topics": ["backpropagation", "activation functions"]
}
```

---

## Stage 2: Blueprint/Skeleton (Outliner Agent)

**Endpoint:** `POST /api/generate/blueprint`

**Response:**
```json
{
  "session_id": "uuid",
  "status": "blueprint_ready",
  "skeleton": {
    "presentation_title": "Introduction to Neural Networks",
    "target_audience": "Graduate Students",
    "slides": [
      {
        "order": 1,
        "title": "Title Slide",
        "content_type": "title",
        "bullet_points": ["Introduction to Neural Networks"],
        "needs_citation": false,
        "needs_diagram": false,
        "needs_equation": false
      },
      {
        "order": 2,
        "title": "What is a Neural Network?",
        "content_type": "content",
        "bullet_points": [
          "Computational model inspired by biological neurons",
          "Consists of layers: input, hidden, output",
          "Learns patterns through training data"
        ],
        "needs_citation": true,
        "citation_topic": "neural network definition",
        "needs_diagram": true,
        "diagram_description": "Simple neural network architecture diagram"
      }
    ]
  }
}
```

**Frontend must:**
- Display skeleton slides for user review
- Allow user to:
  - Reorder slides
  - Edit titles and bullet points
  - Add/remove slides
  - Toggle `needs_citation`, `needs_diagram`, `needs_equation`
- Send modified skeleton with approval

---

## Stage 3: Approval & Generation

**Endpoint:** `POST /api/generate/approve`

**Request:**
```json
{
  "session_id": "uuid",
  "approved": true,
  "modified_skeleton": { ... }  // Optional: user's edits
}
```

**Response:**
```json
{
  "session_id": "uuid",
  "status": "generating",
  "generation_job_id": "job-uuid",
  "message": "Generation started!"
}
```

**Frontend must:**
- Show loading/progress indicator
- Poll status endpoint

---

## Stage 4: Generation Status

**Endpoint:** `GET /api/generate/status/:session_id`

**Response (in progress):**
```json
{
  "session_id": "uuid",
  "status": "generating",
  "stage": "planner",
  "progress_message": "Enriching content with citations...",
  "slides_completed": 0,
  "total_slides": 6
}
```

**Response (completed):**
```json
{
  "session_id": "uuid",
  "status": "completed",
  "result": {
    "success": true,
    "average_visual_score": 0.92,
    "total_citations": 5,
    "slides": [
      {
        "order": 1,
        "html_content": "<!DOCTYPE html>...",
        "visual_score": 0.95,
        "visual_issues": [],
        "iterations": 1
      }
    ]
  }
}
```

**Frontend must:**
- Poll every 2-3 seconds
- Update progress UI based on `stage` and `progress_message`
- Handle `status: "failed"` with error display

---

## Slide HTML Structure

Each slide is delivered as complete HTML with embedded CSS.

**Dimensions:** Exactly 1280×720 pixels (16:9 PowerPoint standard)

**HTML Structure:**
```html
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    /* Theme CSS variables and component styles */
    .slide {
      width: 1280px;
      height: 720px;
      /* ... */
    }
  </style>
</head>
<body>
  <div class="slide" data-id="slide-1">
    <h1 class="slide-title" data-id="title-1">Slide Title</h1>
    <div class="slide-content" data-id="content-1">
      <!-- Components here -->
    </div>
  </div>
</body>
</html>
```

**Frontend must:**
- Render HTML in iframe or shadow DOM (isolated styles)
- Set iframe size to exactly 1280×720
- Scale for display: `transform: scale(0.5)` for preview
- Every element has `data-id` for future click-to-edit

---

## Embedded Assets

### LaTeX Equations
- Pre-rendered to SVG on backend
- Delivered as inline `<svg>` elements
- No client-side MathJax needed

### Mermaid Diagrams
- Pre-rendered to SVG on backend
- Delivered as inline `<svg>` elements
- No client-side Mermaid.js needed

### Images
- URLs provided in `image_url` field
- Frontend may need to proxy for CORS

### Citations
- Formatted according to `citation_style`
- Included in slide HTML as text

---

## Visual QA Scores

Each slide includes quality metrics:

```json
{
  "visual_score": 0.92,      // 0.0 to 1.0
  "visual_issues": [
    "Text slightly small for projected display"
  ],
  "iterations": 2            // QA fix iterations applied
}
```

**Frontend may:**
- Display score badge per slide
- Highlight slides with score < 0.80
- Show issues on hover

---

## Themes

**Endpoint:** `GET /api/themes`

**Response:**
```json
{
  "themes": [
    {
      "id": "academic",
      "name": "Academic",
      "description": "Classic academic presentation style",
      "colors": {
        "primary": "#0056A0",
        "secondary": "#FFD700",
        "background": "#FFFFFF",
        "text_primary": "#1A1A1A"
      }
    },
    {
      "id": "modern",
      "name": "Modern",
      "description": "Clean, contemporary design"
    }
  ]
}
```

**Frontend must:**
- Display theme picker during clarification
- Allow color palette customization
- Show theme preview

---

## Error Handling

**Failed generation:**
```json
{
  "status": "failed",
  "error": "Failed to connect to render service",
  "stage_failed": "pre_render"
}
```

**Frontend must:**
- Display user-friendly error message
- Allow retry from last checkpoint
- Show which stage failed

---

## Export

The backend provides HTML. For other formats:

**PowerPoint (.pptx):**
- Frontend uses library (e.g., pptxgenjs, or any appropriate tool like dom-to-pptx, etc. -whatever is appropriate for the job )
- Insert slide HTML as image or recreate structure

**PDF:**
- Use browser print or html2canvas + jsPDF
- Render at 1280×720 then export

---

## Summary: Frontend Responsibilities

| Area | Frontend Must Handle |
|------|---------------------|
| **Clarification** | Multi-turn Q&A UI, question display, answer collection |
| **Skeleton Review** | Editable slide list, drag-to-reorder, edit bullet points |
| **Generation Progress** | Polling, progress bar, stage indicators |
| **Slide Rendering** | iframe/shadow DOM, 1280×720 iframe, scaling |
| **Theme Selection** | Theme picker, color customization |
| **Visual Scores** | Score badges, issue tooltips |
| **Export** | PPTX/PDF generation from HTML |
| **Error Handling** | Error messages, retry buttons |
