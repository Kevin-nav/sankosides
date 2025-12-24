"""
Generation API Router - Production Ready

Endpoints that interface with the SlideGenerationFlow.
Supports:
- Multi-turn clarification
- Outline review and modification
- SSE streaming of generation progress
- Session management with database persistence
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime
import json
import asyncio

from app.models.schemas import (
    OrderForm,
    Skeleton,
    GeneratedPresentation,
)
from app.crew.flows.slide_generation import (
    SlideGenerationFlow,
    FlowState,
    FlowStatus,
    FlowEventEmitter,
    create_session,
    process_clarification,
    generate_outline,
    approve_outline,
    run_generation,
)
from app.crew.flows.metrics import MetricsCollector
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/generation", tags=["generation"])


# =============================================================================
# In-Memory Session Store (Replace with DB in production)
# =============================================================================

_sessions: Dict[str, FlowState] = {}


def get_session(session_id: str) -> FlowState:
    """Get session from store."""
    if session_id not in _sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return _sessions[session_id]


def save_session(state: FlowState):
    """Save session to store."""
    _sessions[state.session_id] = state


# =============================================================================
# Request/Response Models
# =============================================================================

class StartSessionResponse(BaseModel):
    """Response when starting a new session."""
    session_id: str
    status: str
    message: str


class ClarifyRequest(BaseModel):
    """Request to continue clarification."""
    message: str


class ClarifyResponse(BaseModel):
    """Response from clarification."""
    session_id: str
    complete: bool
    question: Optional[str] = None
    order_form: Optional[Dict] = None
    # NEW: For confirmation flow
    needs_confirmation: bool = False
    summary: Optional[Dict] = None  # Structured summary for UI display
    message: Optional[str] = None  # Friendly message for the user


class OutlineResponse(BaseModel):
    """Response containing the outline."""
    session_id: str
    status: str
    skeleton: Dict


class ApproveRequest(BaseModel):
    """Request to approve/modify outline."""
    modifications: Optional[List[Dict]] = None


class GenerationStartResponse(BaseModel):
    """Response when generation starts."""
    session_id: str
    status: str
    total_slides: int
    message: str


class SessionStatusResponse(BaseModel):
    """Full session status."""
    session_id: str
    status: str
    current_stage: str
    slides_completed: int
    total_slides: int
    order_form: Optional[Dict] = None
    skeleton: Optional[Dict] = None
    qa_score: Optional[float] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/start", response_model=StartSessionResponse)
async def start_session():
    """
    Start a new generation session.
    
    Returns a session_id to use for subsequent calls.
    Begins in AWAITING_CLARIFICATION status.
    """
    state = await create_session()
    save_session(state)
    
    return StartSessionResponse(
        session_id=state.session_id,
        status=state.status,
        message="Session created. Send your first message to /clarify/{session_id}",
    )


@router.post("/clarify/{session_id}", response_model=ClarifyResponse)
async def clarify_session(session_id: str, request: ClarifyRequest):
    """
    Continue the clarification conversation.
    
    Send user messages here until the OrderForm is complete.
    The agent will ask follow-up questions until it has enough info.
    
    When complete=True, proceed to /outline/{session_id}
    """
    state = get_session(session_id)
    
    if state.status not in [FlowStatus.AWAITING_CLARIFICATION, "awaiting_clarification"]:
        raise HTTPException(
            status_code=400,
            detail=f"Session not in clarification phase. Status: {state.status}",
        )
    
    try:
        result = await process_clarification(session_id, request.message, state)
        save_session(state)
        
        return ClarifyResponse(
            session_id=session_id,
            complete=result.get("complete", False),
            question=result.get("question"),
            order_form=result.get("order_form"),
            needs_confirmation=result.get("needs_confirmation", False),
            summary=result.get("summary"),
            message=result.get("message"),
        )
    except Exception as e:
        logger.error(f"Clarification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/confirm/{session_id}", response_model=ClarifyResponse)
async def confirm_clarification(session_id: str):
    """
    Confirm the gathered clarification info.
    
    Called when user clicks "Approve" button on the confirmation UI.
    Finalizes the OrderForm and moves to CLARIFICATION_COMPLETE status.
    
    After this, proceed to /outline/{session_id}
    """
    state = get_session(session_id)
    
    if state.status not in [FlowStatus.AWAITING_CLARIFICATION, "awaiting_clarification"]:
        raise HTTPException(
            status_code=400,
            detail=f"Session not in clarification phase. Status: {state.status}",
        )
    
    if not state.gathered_info:
        raise HTTPException(
            status_code=400,
            detail="No gathered info to confirm. Continue clarification first.",
        )
    
    if not state.gathered_info.is_complete_enough():
        raise HTTPException(
            status_code=400,
            detail="Not enough info gathered. Missing: " + ", ".join(state.gathered_info.get_missing_required()),
        )
    
    # Mark as confirmed and create final OrderForm
    state.gathered_info.user_confirmed = True
    
    # Create OrderForm from gathered info
    from app.models.schemas import OrderForm
    order_form = OrderForm(
        presentation_title=state.gathered_info.title or "Untitled Presentation",
        target_audience=state.gathered_info.audience or "General audience",
        target_slides=state.gathered_info.slide_count or 10,
        focus_areas=state.gathered_info.focus_areas,
        key_topics=state.gathered_info.key_topics,
        tone=state.gathered_info.tone or "academic",
        emphasis_style=state.gathered_info.emphasis_style or "detailed",
        citation_style=state.gathered_info.citation_style or "apa",
        references_placement=state.gathered_info.references_placement or "last_slide",
        theme_id=state.gathered_info.theme or "modern",
        include_speaker_notes=state.gathered_info.include_speaker_notes or True,
        special_requests=state.gathered_info.special_requests or "",
        is_complete=True,
    )
    
    state.order_form = order_form
    state.status = FlowStatus.CLARIFICATION_COMPLETE
    save_session(state)
    
    return ClarifyResponse(
        session_id=session_id,
        complete=True,
        order_form=order_form.model_dump(),
        message="Requirements confirmed! You can now proceed to generate the outline.",
    )


@router.post("/outline/{session_id}", response_model=OutlineResponse)
async def get_outline(session_id: str):
    """
    Generate the presentation outline.
    
    Only callable after clarification is complete.
    Returns the skeleton for user review - user can then approve
    or modify via /approve-outline/{session_id}
    """
    state = get_session(session_id)
    
    if state.status not in [FlowStatus.CLARIFICATION_COMPLETE, "clarification_complete"]:
        raise HTTPException(
            status_code=400,
            detail=f"Clarification not complete. Status: {state.status}",
        )
    
    try:
        skeleton = await generate_outline(session_id, state)
        save_session(state)
        
        return OutlineResponse(
            session_id=session_id,
            status=state.status,
            skeleton=skeleton.model_dump(),
        )
    except Exception as e:
        logger.error(f"Outline generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/approve-outline/{session_id}", response_model=OutlineResponse)
async def approve_outline_endpoint(session_id: str, request: ApproveRequest):
    """
    Approve the outline (with optional modifications).
    
    Modifications are a list of actions:
    - {"action": "add", "order": 3, "title": "New Slide", "content_type": "content"}
    - {"action": "remove", "order": 2}
    - {"action": "modify", "order": 1, "title": "New Title"}
    - {"action": "reorder", "new_order": [1, 3, 2, 4]}
    
    After approval, call /generate/{session_id} to start generation.
    """
    state = get_session(session_id)
    
    if state.status not in [FlowStatus.AWAITING_OUTLINE_APPROVAL, "awaiting_outline_approval"]:
        raise HTTPException(
            status_code=400,
            detail=f"No outline awaiting approval. Status: {state.status}",
        )
    
    try:
        skeleton = await approve_outline(session_id, state, request.modifications)
        save_session(state)
        
        return OutlineResponse(
            session_id=session_id,
            status=state.status,
            skeleton=skeleton.model_dump(),
        )
    except Exception as e:
        logger.error(f"Outline approval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate/{session_id}", response_model=GenerationStartResponse)
async def start_generation(session_id: str, background_tasks: BackgroundTasks):
    """
    Start the generation pipeline.
    
    This runs asynchronously in the background.
    Use /stream/{session_id} for real-time progress.
    Use /status/{session_id} to poll status.
    """
    state = get_session(session_id)
    
    if state.status not in [FlowStatus.OUTLINE_APPROVED, "outline_approved"]:
        raise HTTPException(
            status_code=400,
            detail=f"Outline not approved. Status: {state.status}",
        )
    
    # Start generation in background
    background_tasks.add_task(_run_generation_task, session_id, state)
    
    return GenerationStartResponse(
        session_id=session_id,
        status="generating",
        total_slides=state.total_slides,
        message="Generation started. Use /stream/{session_id} for progress.",
    )


async def _run_generation_task(session_id: str, state: FlowState):
    """Background task for generation."""
    try:
        await run_generation(session_id, state)
        save_session(state)
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        state.status = FlowStatus.FAILED
        state.error_message = str(e)
        save_session(state)


@router.get("/stream/{session_id}")
async def stream_progress(session_id: str):
    """
    Stream generation progress via Server-Sent Events (SSE).
    
    Events:
    - stage_start: {"stage": "planner"}
    - stage_complete: {"stage": "planner", "result": {...}}
    - slide_progress: {"slide_order": 1, "total": 10, "status": "generating"}
    - error: {"message": "...", "stage": "..."}
    - complete: {"slides_count": 10}
    """
    state = get_session(session_id)
    
    async def event_generator() -> AsyncGenerator[str, None]:
        # Track state changes
        last_stage = state.current_stage
        last_slides = state.slides_completed
        
        while state.status in [FlowStatus.GENERATING, "generating", FlowStatus.QA_IN_PROGRESS]:
            # Check for stage changes
            if state.current_stage != last_stage:
                yield f"event: stage_start\ndata: {json.dumps({'stage': state.current_stage})}\n\n"
                last_stage = state.current_stage
            
            # Check for slide progress
            if state.slides_completed != last_slides:
                yield f"event: slide_progress\ndata: {json.dumps({'slide_order': state.slides_completed, 'total': state.total_slides})}\n\n"
                last_slides = state.slides_completed
            
            await asyncio.sleep(0.5)
        
        # Final event
        if state.status == FlowStatus.COMPLETED:
            yield f"event: complete\ndata: {json.dumps({'slides_count': state.total_slides})}\n\n"
        elif state.status == FlowStatus.FAILED:
            yield f"event: error\ndata: {json.dumps({'message': state.error_message or 'Unknown error'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )


@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_status(session_id: str):
    """
    Get current session status.
    
    Use this to poll for completion if not using SSE streaming.
    """
    state = get_session(session_id)
    
    return SessionStatusResponse(
        session_id=session_id,
        status=state.status,
        current_stage=state.current_stage,
        slides_completed=state.slides_completed,
        total_slides=state.total_slides,
        order_form=state.order_form.model_dump() if state.order_form else None,
        skeleton=state.skeleton.model_dump() if state.skeleton else None,
        qa_score=state.qa_report.average_score if state.qa_report else None,
    )


@router.get("/result/{session_id}")
async def get_result(session_id: str):
    """
    Get the final generated presentation.
    
    Only available after generation completes successfully.
    """
    state = get_session(session_id)
    
    if state.status not in [FlowStatus.COMPLETED, "completed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Generation not complete. Status: {state.status}",
        )
    
    if not state.generated_presentation:
        raise HTTPException(status_code=500, detail="No presentation found")
    
    return {
        "session_id": session_id,
        "presentation": state.generated_presentation.model_dump(),
        "qa_report": state.qa_report.model_dump() if state.qa_report else None,
    }


# =============================================================================
# Quick-Start Endpoint (Skip Clarification)
# =============================================================================

@router.post("/quick-start")
async def quick_start(
    title: str,
    topic: str,
    slides_count: int = 8,
    audience: str = "general",
    background_tasks: BackgroundTasks = None,
):
    """
    Quick start generation with minimal input.
    
    Skips clarification and generates outline automatically.
    Use for demos or when user provides essential info upfront.
    """
    # Create session with pre-filled OrderForm
    state = await create_session()
    state.order_form = OrderForm(
        presentation_title=title,
        target_audience=audience,
        key_topics=[topic],
        target_slides=slides_count,
        is_complete=True,
    )
    state.status = FlowStatus.CLARIFICATION_COMPLETE
    save_session(state)
    
    # Generate outline
    skeleton = await generate_outline(state.session_id, state)
    save_session(state)
    
    # Auto-approve
    await approve_outline(state.session_id, state)
    save_session(state)
    
    # Start generation in background
    if background_tasks:
        background_tasks.add_task(_run_generation_task, state.session_id, state)
    
    return {
        "session_id": state.session_id,
        "status": "generating",
        "skeleton": skeleton.model_dump(),
        "message": "Generation started. Use /stream/{session_id} for progress.",
    }


# =============================================================================
# Metrics Endpoint (For Frontend Testing Ground)
# =============================================================================

@router.get("/metrics/{session_id}")
async def get_metrics(session_id: str):
    """
    Get token usage metrics for a session.
    
    Returns detailed token usage per agent for display in the
    frontend testing ground/playground.
    
    Response includes:
    - Per-agent: input_tokens, output_tokens, thinking_tokens, cost_usd
    - Totals: all tokens aggregated, total cost
    - Call history: last 10 API calls per agent
    """
    # Get session to validate it exists
    state = get_session(session_id)
    
    # Get metrics collector
    collector = MetricsCollector.get(session_id)
    if not collector:
        return {
            "session_id": session_id,
            "message": "No metrics recorded yet",
            "totals": {
                "input_tokens": 0,
                "output_tokens": 0,
                "thinking_tokens": 0,
                "total_tokens": 0,
                "cost_usd": 0,
                "api_calls": 0,
            },
            "agents": {},
        }
    
    return collector.to_dict()


@router.get("/metrics/{session_id}/summary")
async def get_metrics_summary(session_id: str):
    """
    Get a concise token usage summary.
    
    Useful for quick display in UI headers/footers.
    """
    state = get_session(session_id)
    collector = MetricsCollector.get(session_id)
    
    if not collector:
        return {
            "session_id": session_id,
            "total_tokens": 0,
            "cost_usd": 0,
            "api_calls": 0,
        }
    
    metrics = collector.get_metrics()
    return {
        "session_id": session_id,
        "input_tokens": metrics.total_input_tokens,
        "output_tokens": metrics.total_output_tokens,
        "thinking_tokens": metrics.total_thinking_tokens,
        "total_tokens": metrics.total_tokens,
        "cost_usd": round(metrics.total_cost_usd, 6),
        "api_calls": metrics.total_api_calls,
        "status": state.status,
    }

