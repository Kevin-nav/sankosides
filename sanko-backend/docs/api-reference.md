# API Reference

Complete documentation of all SankoSlides Backend API endpoints.

## Table of Contents

- [Authentication](#authentication)
- [Generation Flow Endpoints](#generation-flow-endpoints)
- [Metrics Endpoints](#metrics-endpoints)
- [Utility Endpoints](#utility-endpoints)
- [Response Formats](#response-formats)
- [Error Handling](#error-handling)

---

## Authentication

Currently, the API does not require authentication for development. In production, implement:

- Bearer token authentication via `Authorization` header
- Session-based auth for frontend integration
- Rate limiting per API key

---

## Generation Flow Endpoints

The generation flow follows a specific sequence:

```
start → clarify (repeat) → outline → approve-outline → generate → stream/result
```

### POST `/api/generation/start`

Create a new generation session.

**Request:** None required

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "awaiting_clarification",
  "message": "Session created. Send your first message to /clarify/{session_id}"
}
```

**Status Codes:**
- `200`: Session created successfully
- `500`: Internal server error

---

### POST `/api/generation/clarify/{session_id}`

Continue the multi-turn clarification conversation. The AI agent will ask follow-up questions until it has enough information to create the presentation.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string (UUID) | Session identifier from `/start` |

**Request Body:**
```json
{
  "message": "I want a presentation about machine learning for my CS 301 class"
}
```

**Response (More questions needed):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "complete": false,
  "question": "How many slides would you like? And should I focus on any particular ML topics like neural networks or decision trees?",
  "order_form": null
}
```

**Response (Clarification complete):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "complete": true,
  "question": null,
  "order_form": {
    "presentation_title": "Introduction to Machine Learning",
    "target_audience": "CS 301 undergraduate students",
    "target_slides": 10,
    "theme_id": "academic",
    "citation_style": "ieee",
    "key_topics": ["Neural Networks", "Decision Trees", "Model Evaluation"],
    "focus_areas": ["Neural Networks"],
    "emphasis_style": "detailed",
    "is_complete": true
  }
}
```

**Status Codes:**
- `200`: Message processed
- `400`: Session not in clarification phase
- `404`: Session not found
- `500`: Agent error

---

### POST `/api/generation/outline/{session_id}`

Generate the presentation skeleton/outline for user review. Only callable after clarification is complete.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string (UUID) | Session identifier |

**Request:** None required

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "awaiting_outline_approval",
  "skeleton": {
    "presentation_title": "Introduction to Machine Learning",
    "target_audience": "CS 301 undergraduate students",
    "narrative_arc": "From fundamentals to practical applications",
    "slides": [
      {
        "order": 1,
        "title": "Introduction to Machine Learning",
        "content_type": "title",
        "description": "Title slide with course context",
        "needs_diagram": false,
        "needs_equation": false,
        "needs_citation": false
      },
      {
        "order": 2,
        "title": "What is Machine Learning?",
        "content_type": "content",
        "description": "Definition and types of ML",
        "needs_diagram": true,
        "needs_equation": false,
        "needs_citation": true,
        "citation_topic": "machine learning definition"
      }
      // ... more slides
    ],
    "estimated_duration_minutes": 20
  }
}
```

**Status Codes:**
- `200`: Outline generated
- `400`: Clarification not complete
- `404`: Session not found

---

### POST `/api/generation/approve-outline/{session_id}`

Approve the outline with optional modifications. After approval, the presentation can be generated.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string (UUID) | Session identifier |

**Request Body:**
```json
{
  "modifications": [
    {
      "action": "add",
      "order": 5,
      "title": "Case Study: Image Classification",
      "content_type": "content",
      "description": "Real-world CNN application"
    },
    {
      "action": "remove",
      "order": 8
    },
    {
      "action": "modify",
      "order": 3,
      "title": "Supervised vs Unsupervised Learning",
      "needs_diagram": true
    },
    {
      "action": "reorder",
      "new_order": [1, 2, 4, 3, 5, 6, 7]
    }
  ]
}
```

**Modification Actions:**

| Action | Required Fields | Description |
|--------|-----------------|-------------|
| `add` | `order`, `title`, `content_type` | Add new slide |
| `remove` | `order` | Remove slide by position |
| `modify` | `order` + any fields to change | Edit existing slide |
| `reorder` | `new_order` (array of positions) | Reorder all slides |

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "outline_approved",
  "skeleton": { /* updated skeleton */ }
}
```

---

### POST `/api/generation/generate/{session_id}`

Start the asynchronous generation pipeline. This runs in the background.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string (UUID) | Session identifier |

**Request:** None required

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "generating",
  "total_slides": 10,
  "message": "Generation started. Use /stream/{session_id} for progress."
}
```

**Status Codes:**
- `200`: Generation started
- `400`: Outline not approved
- `404`: Session not found

---

### GET `/api/generation/stream/{session_id}`

Stream generation progress via Server-Sent Events (SSE). Connect to this endpoint to receive real-time updates.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string (UUID) | Session identifier |

**Event Types:**

| Event | Data | Description |
|-------|------|-------------|
| `stage_start` | `{"stage": "planner"}` | Pipeline stage started |
| `stage_complete` | `{"stage": "planner", "result": {...}}` | Stage finished |
| `slide_progress` | `{"slide_order": 3, "total": 10, "status": "generating"}` | Slide being processed |
| `error` | `{"message": "...", "stage": "refiner"}` | Error occurred |
| `complete` | `{"slides_count": 10}` | Generation finished |

**Example SSE Stream:**
```
event: stage_start
data: {"stage": "planner"}

event: slide_progress
data: {"slide_order": 1, "total": 10, "status": "planning"}

event: stage_complete
data: {"stage": "planner", "result": {"slides_planned": 10}}

event: stage_start
data: {"stage": "refiner"}

... more events ...

event: complete
data: {"slides_count": 10}
```

**Frontend Usage:**
```javascript
const eventSource = new EventSource(`/api/generation/stream/${sessionId}`);

eventSource.addEventListener('slide_progress', (e) => {
  const data = JSON.parse(e.data);
  updateProgressBar(data.slide_order, data.total);
});

eventSource.addEventListener('complete', (e) => {
  eventSource.close();
  fetchResult(sessionId);
});

eventSource.addEventListener('error', (e) => {
  console.error('Generation error:', e.data);
  eventSource.close();
});
```

---

### GET `/api/generation/status/{session_id}`

Poll current session status. Use this if not using SSE streaming.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string (UUID) | Session identifier |

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "generating",
  "current_stage": "generator",
  "slides_completed": 6,
  "total_slides": 10,
  "order_form": { /* OrderForm object */ },
  "skeleton": { /* Skeleton object */ },
  "qa_score": null
}
```

**Status Values:**

| Status | Description |
|--------|-------------|
| `awaiting_clarification` | Waiting for user messages |
| `clarification_complete` | Ready to generate outline |
| `awaiting_outline_approval` | Outline ready for review |
| `outline_approved` | Ready to start generation |
| `generating` | Pipeline running |
| `qa_in_progress` | Visual QA checking slides |
| `completed` | Generation finished successfully |
| `failed` | Error occurred |

---

### GET `/api/generation/result/{session_id}`

Get the final generated presentation. Only available after generation completes.

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string (UUID) | Session identifier |

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "presentation": {
    "title": "Introduction to Machine Learning",
    "theme_id": "academic",
    "slides": [
      {
        "order": 1,
        "title": "Introduction to Machine Learning",
        "theme_id": "academic",
        "rendered_html": "<div class=\"slide slide-1\" data-template=\"title\">...</div>",
        "speaker_notes": "Welcome the class and introduce the topic..."
      }
      // ... more slides
    ],
    "total_slides": 10
  },
  "qa_report": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "slides": [
      {
        "slide_order": 1,
        "score": 97.5,
        "issues": [],
        "passed": true,
        "iterations": 1
      }
      // ... more results
    ],
    "average_score": 96.2,
    "all_passed": true,
    "total_iterations": 1
  }
}
```

---

## Metrics Endpoints

### GET `/api/generation/metrics/{session_id}`

Get detailed token usage metrics per agent.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-12-21T20:30:00Z",
  "totals": {
    "input_tokens": 45000,
    "output_tokens": 28000,
    "thinking_tokens": 8500,
    "total_tokens": 81500,
    "cost_usd": 0.1234,
    "api_calls": 12,
    "pipeline_duration_ms": 45230
  },
  "agents": {
    "clarifier": {
      "agent_name": "clarifier",
      "calls": 3,
      "input_tokens": 8000,
      "output_tokens": 4500,
      "thinking_tokens": 1200,
      "total_tokens": 13700,
      "cost_usd": 0.0178,
      "avg_duration_ms": 1523.5,
      "call_history": [/* last 10 calls */]
    },
    "planner": { /* ... */ },
    "refiner": { /* ... */ },
    "generator": { /* ... */ },
    "visual_qa": { /* ... */ }
  }
}
```

---

### GET `/api/generation/metrics/{session_id}/summary`

Get a concise token usage summary for UI display.

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "input_tokens": 45000,
  "output_tokens": 28000,
  "thinking_tokens": 8500,
  "total_tokens": 81500,
  "cost_usd": 0.1234,
  "api_calls": 12,
  "status": "completed"
}
```

---

### POST `/api/generation/quick-start`

Skip clarification and generate immediately with minimal input. Useful for demos.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | string | required | Presentation title |
| `topic` | string | required | Main topic |
| `slides_count` | int | 8 | Number of slides |
| `audience` | string | "general" | Target audience |

**Example:**
```
POST /api/generation/quick-start?title=Machine%20Learning&topic=neural%20networks&slides_count=10&audience=students
```

**Response:**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "generating",
  "skeleton": { /* auto-generated skeleton */ },
  "message": "Generation started. Use /stream/{session_id} for progress."
}
```

---

## Utility Endpoints

### GET `/`

Get API information.

**Response:**
```json
{
  "name": "SankoSlides API",
  "version": "0.2.0",
  "status": "running",
  "architecture": "CrewAI Multi-Agent",
  "docs": "/docs"
}
```

### GET `/health`

Health check endpoint for monitoring.

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Response Formats

### Pagination

Future endpoints that return lists will use:

```json
{
  "items": [...],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "has_next": true
}
```

### Timestamps

All timestamps use ISO 8601 format: `2025-12-21T20:30:00Z`

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Session not found"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| `200` | Success |
| `400` | Bad request / Invalid state |
| `404` | Resource not found |
| `422` | Validation error |
| `500` | Internal server error |

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Session not found" | Invalid session ID | Start a new session |
| "Session not in clarification phase" | Called clarify after completion | Proceed to next step |
| "Clarification not complete" | Called outline too early | Continue clarifying |
| "Outline not approved" | Called generate before approving | Approve the outline first |
| "Generation not complete" | Called result too early | Wait for completion |

---

## Rate Limits

Development: No limits

Production (planned):
- 100 requests/minute per API key
- 10 concurrent generation sessions
- 1000 slides/day per account
