# Flow Architecture

How the SankoSlides generation pipeline is orchestrated using CrewAI Flows.

## Table of Contents

- [Overview](#overview)
- [Flow State Management](#flow-state-management)
- [Pause Points](#pause-points)
- [Event Streaming](#event-streaming)
- [Error Recovery](#error-recovery)
- [Database Persistence](#database-persistence)

---

## Overview

SankoSlides uses an **event-driven flow** architecture that:

1. Pauses at user review points
2. Persists state to database
3. Streams progress via SSE
4. Handles failures gracefully

```
┌────────────────────────────────────────────────────────────────────┐
│                     SlideGenerationFlow                            │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  ┌──────────┐                                                      │
│  │  START   │                                                      │
│  └────┬─────┘                                                      │
│       │                                                            │
│       ▼                                                            │
│  ┌──────────┐     ┌──────────┐                                     │
│  │ Clarifier│────▶│ Complete?│───No──▶ [PAUSE: awaiting_input]    │
│  └──────────┘     └────┬─────┘                                     │
│                        │ Yes                                       │
│                        ▼                                           │
│                   ┌──────────┐                                     │
│                   │ Outliner │────▶ [PAUSE: awaiting_approval]    │
│                   └────┬─────┘                                     │
│                        │ Approved                                  │
│                        ▼                                           │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌───────────┐     │
│  │ Planner  │───▶│ Refiner  │───▶│Generator │───▶│ VisualQA│     │
│  └──────────┘    └──────────┘    └──────────┘    └────┬──────┘     │
│                                                       │            │
│                                          Pass? ───────┼─── Yes ──▶ COMPLETE
│                                                       │            │
│                                                      No            │
│                                                       │            │
│                                                       ▼            │
│                                                  ┌──────────┐      │
│                                                  │  Helper  │      │
│                                                  └────┬─────┘      │
│                                                       │            │
│                                          ┌────────────┼─────────┐  │
│                                          │            │         │  │
│                                      Direct Fix    Retry    Escalate
│                                          │            │         │  │
│                                          ▼            ▼         ▼  │
│                                      COMPLETE    Loop Back   FAILED │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Flow State Management

### FlowState Model

The `FlowState` model holds all pipeline data and is serializable to the database.

```python
class FlowState(BaseModel):
    # Session
    session_id: str
    user_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Pipeline outputs (populated progressively)
    order_form: Optional[OrderForm]
    skeleton: Optional[Skeleton]
    planned_content: Optional[PlannedContent]
    refined_content: Optional[RefinedContent]
    generated_presentation: Optional[GeneratedPresentation]
    qa_report: Optional[QAReport]
    
    # Status tracking
    status: FlowStatus
    current_stage: str
    
    # QA loop tracking
    qa_loops: int
    max_qa_loops: int = 3
    
    # Helper retry tracking
    helper_attempts: Dict[str, int]
    failure_context: Optional[Dict]
    
    # Progress
    slides_completed: int
    total_slides: int
    error_message: Optional[str]
```

### Status Flow

```
awaiting_clarification
        │
        ▼ (clarify until complete)
clarification_complete
        │
        ▼ (generate outline)
awaiting_outline_approval
        │
        ▼ (user approves)
outline_approved
        │
        ▼ (start generation)
generating
        │
        ├──▶ qa_in_progress
        │           │
        │           ▼
        │    ┌─────────────┐
        │    │  Pass: 95%? │
        │    └─────────────┘
        │           │
        │    Yes ◀──┴──▶ No (retry)
        │
        ▼
   completed  ───or───  failed
```

---

## Pause Points

The flow has two user interaction points where it pauses.

### 1. Clarification Pause

**Status:** `awaiting_clarification`

**Behavior:**
- Flow waits for user message
- Each message triggers Clarifier agent
- Repeats until `OrderForm.is_complete = True`

**Resume:** Call `POST /api/generation/clarify/{session_id}`

### 2. Outline Approval Pause

**Status:** `awaiting_outline_approval`

**Behavior:**
- Skeleton is generated and saved
- User can review and modify
- Flow waits for approval

**Resume:** Call `POST /api/generation/approve-outline/{session_id}`

### Implementation

```python
class SlideGenerationFlow:
    async def generate_outline(self) -> Skeleton:
        # Generate skeleton...
        self.state.skeleton = skeleton
        self.state.status = FlowStatus.AWAITING_OUTLINE_APPROVAL
        
        # Emit pause event
        await self.emitter.pause_for_review("outline", {
            "skeleton": skeleton.model_dump(),
        })
        
        # Flow returns here - API handles resume
        return skeleton
    
    async def approve_outline(self, modifications=None) -> Skeleton:
        # Apply modifications if any...
        self.state.status = FlowStatus.OUTLINE_APPROVED
        
        # Flow can now continue to generation
        return self.state.skeleton
```

---

## Event Streaming

Real-time progress updates via Server-Sent Events (SSE).

### FlowEventEmitter

```python
class FlowEventEmitter:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.listeners: List[Callable] = []
    
    async def emit(self, event_type: str, data: Dict):
        event = {
            "type": event_type,
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            **data,
        }
        for listener in self.listeners:
            await listener(event)
```

### Event Types

| Event | When Emitted | Data |
|-------|--------------|------|
| `stage_start` | Stage begins | `{stage: "planner"}` |
| `stage_complete` | Stage finishes | `{stage: "planner", result: {...}}` |
| `slide_progress` | Slide processed | `{slide_order: 3, total: 10, status: "generating"}` |
| `pause` | Awaiting user input | `{review_type: "outline", skeleton: {...}}` |
| `error` | Error occurred | `{message: "...", stage: "refiner"}` |
| `complete` | Generation finished | `{slides_count: 10}` |

### Frontend Integration

```javascript
// Connect to SSE stream
const eventSource = new EventSource(`/api/generation/stream/${sessionId}`);

// Handle events
eventSource.addEventListener('stage_start', (e) => {
  const { stage } = JSON.parse(e.data);
  setCurrentStage(stage);
});

eventSource.addEventListener('slide_progress', (e) => {
  const { slide_order, total } = JSON.parse(e.data);
  setProgress((slide_order / total) * 100);
});

eventSource.addEventListener('complete', () => {
  eventSource.close();
  fetchFinalResult();
});

eventSource.onerror = () => {
  eventSource.close();
  handleError();
};
```

---

## Error Recovery

### Failure Handling Flow

```
┌─────────────────────────────────────────────────────────┐
│                    Stage Failure                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │  Create FailureCtx  │
              │  - failing_agent    │
              │  - failure_type     │
              │  - error_message    │
              └─────────────────────┘
                          │
                          ▼
              ┌─────────────────────┐
              │  Check RetryBudget  │
              │  (max 2 per agent)  │
              └─────────────────────┘
                          │
             ┌────────────┴────────────┐
             │                         │
        Can Retry              Budget Exhausted
             │                         │
             ▼                         ▼
    ┌─────────────────┐      ┌─────────────────┐
    │  Helper Agent   │      │    Escalate     │
    │  - Analyze      │      │  - Save report  │
    │  - Add guards   │      │  - Notify user  │
    └─────────────────┘      └─────────────────┘
             │
             ▼
    ┌─────────────────┐
    │  Retry Agent    │
    │  with guardrails│
    └─────────────────┘
```

### Retry Budget

```python
class RetryBudget:
    MAX_RETRIES = 2
    
    def __init__(self):
        self.attempts: Dict[str, int] = {}
    
    def can_retry(self, agent_name: str) -> bool:
        return self.attempts.get(agent_name, 0) < self.MAX_RETRIES
    
    def record_attempt(self, agent_name: str):
        self.attempts[agent_name] = self.attempts.get(agent_name, 0) + 1
```

### Guardrail Injection

When retrying, the Helper agent generates guardrails:

```python
def build_guardrail_prompt(context: FailureContext) -> str:
    return f"""
CRITICAL: Previous attempt failed.

FAILURE DETAILS:
- Agent: {context.failing_agent}
- Error: {context.error_message}
- Attempt: {context.previous_attempts + 1} of 2

GUARDRAILS TO FOLLOW:
1. {specific_fix_based_on_error}
2. {another_constraint}
3. Double-check output format

DO NOT repeat the same mistake.
"""
```

---

## Database Persistence

### Session Storage

**Table:** `playground_sessions`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `status` | VARCHAR | Current flow status |
| `current_stage` | VARCHAR | Active stage name |
| `order_form` | JSONB | OrderForm data |
| `skeleton` | JSONB | Skeleton data |
| `planned_content` | JSONB | PlannedContent data |
| `refined_content` | JSONB | RefinedContent data |
| `generated_slides` | JSONB | Final slides |
| `qa_loops_count` | INT | QA iterations |
| `helper_retries` | INT | Helper attempts |
| `final_qa_score` | FLOAT | Average QA score |
| `created_at` | TIMESTAMP | Session start |
| `updated_at` | TIMESTAMP | Last update |

### Failure Reports

**Table:** `failure_reports`

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `session_id` | UUID | Foreign key |
| `failing_stage` | VARCHAR | Stage that failed |
| `error_type` | VARCHAR | Error classification |
| `error_message` | TEXT | Full error |
| `stack_trace` | TEXT | Traceback |
| `helper_attempts` | INT | Recovery attempts |
| `resolution` | VARCHAR | How it was resolved |
| `created_at` | TIMESTAMP | When failure occurred |

### State Persistence

```python
async def save_state(self):
    """Save current state to database."""
    data = self.state.to_db_dict()
    
    async with get_async_session() as session:
        stmt = update(PlaygroundSession).where(
            PlaygroundSession.id == self.state.session_id
        ).values(**data)
        await session.execute(stmt)
        await session.commit()

async def load_state(self, session_id: str):
    """Restore state from database."""
    async with get_async_session() as session:
        result = await session.execute(
            select(PlaygroundSession).where(
                PlaygroundSession.id == session_id
            )
        )
        db_session = result.scalar_one_or_none()
        if db_session:
            self.state = FlowState.from_db(db_session.__dict__)
```

---

## Parallel Slide Generation

For performance, slides are generated in parallel during the Generator stage:

```python
async def _run_generator(self):
    # Create tasks for parallel execution
    tasks = [
        self._generate_slide_html(slide)
        for slide in self.state.refined_content.slides
    ]
    
    # Run all slides concurrently
    generated_slides = await asyncio.gather(*tasks)
    
    self.state.generated_presentation = GeneratedPresentation(
        slides=generated_slides,
        # ...
    )
```

### Progress Tracking

```python
async def _generate_slide_html(self, slide: RefinedSlide) -> GeneratedSlide:
    # Emit progress event
    await self.emitter.slide_progress(
        slide.order, 
        self.state.total_slides,
        "generating"
    )
    
    # Generate HTML...
    html = self._build_slide_html(slide)
    
    # Update counter
    self.state.slides_completed += 1
    
    return GeneratedSlide(...)
```

---

## Custom Flow Extensions

### Adding a New Stage

1. **Add stage method:**

```python
async def _run_new_stage(self):
    await self.emitter.stage_start("new_stage")
    self.state.current_stage = "new_stage"
    
    # Do work...
    
    await self.emitter.stage_complete("new_stage", result)
```

2. **Insert in pipeline sequence**

3. **Add to status enum if needed**

### Adding a New Pause Point

```python
async def my_stage_with_pause(self):
    # Generate something for review
    output = await self._generate_something()
    
    # Update state
    self.state.my_output = output
    self.state.status = FlowStatus.AWAITING_MY_APPROVAL
    
    # Emit pause event
    await self.emitter.pause_for_review("my_review", {
        "output": output.model_dump(),
    })
    
    return output

async def approve_my_output(self, modifications=None):
    # Apply mods...
    self.state.status = FlowStatus.MY_APPROVAL_COMPLETE
    return self.state.my_output
```
