"""
Generation Router

Handles the slide generation workflow:
1. Start a new generation session
2. Handle clarification Q&A
3. Review and approve blueprint
4. Execute generation
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
import json
import os
import re
import asyncio


from app.config import Settings, get_settings
from app.logging_config import get_logger
from app.services.gemini import GeminiInteractionsClient
from app.services.metrics import get_metrics_tracker
from app.pipeline import SlideGenerationPipeline, PipelineResult
from app.agents.synthesizer import Skeleton, SkeletonSlide
from app import prompts

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class GenerationMode(str, Enum):
    """The three generation engines from the plan."""
    REPLICA = "replica"        # Image of existing slide -> recreate
    SYNTHESIS = "synthesis"    # Documents -> extract and structure
    DEEP_RESEARCH = "deep_research"  # Topic -> research and create


class StartGenerationRequest(BaseModel):
    """Request to start a new generation session."""
    mode: GenerationMode
    topic: Optional[str] = None  # For DEEP_RESEARCH mode
    project_id: Optional[str] = None  # Link to existing project
    university_profile: Optional[Dict[str, Any]] = None  # User's university settings
    prompt_overrides: Optional[Dict[str, str]] = None  # For Playground


class StartGenerationResponse(BaseModel):
    """Response after starting generation."""
    session_id: str
    interaction_id: Optional[str] = None
    status: str
    clarification_question: Optional[str] = None
    message: str


class ClarifyRequest(BaseModel):
    """User's answer to a clarification question."""
    session_id: str
    answer: str


class ClarifyResponse(BaseModel):
    """Response after processing clarification."""
    session_id: str
    status: str
    next_question: Optional[str] = None
    blueprint_ready: bool = False
    message: str
    thinking: Optional[str] = None  # Agent's thought process (observability)


class BlueprintSlide(BaseModel):
    """A single slide in the blueprint."""
    order: int
    title: str
    content_type: str  # "title", "overview", "content", "conclusion", etc.
    key_points: List[str]
    has_equation: bool = False
    has_diagram: bool = False


class BlueprintResponse(BaseModel):
    """The slide blueprint for user approval."""
    session_id: str
    title: str
    slide_count: int
    slides: List[BlueprintSlide]
    estimated_generation_time_seconds: int


class ApproveRequest(BaseModel):
    """Request to approve the blueprint and start generation."""
    session_id: str
    modifications: Optional[Dict[str, Any]] = None  # Optional user tweaks


class ApproveResponse(BaseModel):
    """Response after approving blueprint."""
    session_id: str
    status: str
    message: str
    generation_job_id: Optional[str] = None


# ============================================================================
# Session Store (JSON File Backend for Dev Persistence)
# ============================================================================

SESSION_FILE = "sessions.json"

def load_sessions() -> Dict[str, Dict[str, Any]]:
    """Load sessions from local JSON file."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load sessions: {e}")
            return {}
    return {}

def save_sessions():
    """Save sessions to local JSON file."""
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        print(f"Failed to save sessions: {e}")


def parse_blueprint_to_skeleton(session: Dict[str, Any]) -> "Skeleton":
    """
    Parse blueprint_raw JSON from session and convert to Skeleton model.
    
    Args:
        session: Session dict containing blueprint_raw
        
    Returns:
        Skeleton with all slides from the blueprint
    """
    raw_content = session.get("blueprint_raw", "")
    
    # Clean markdown code blocks
    cleaned = re.sub(r"```json\s*", "", raw_content)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    
    try:
        data = json.loads(cleaned)
        
        if "slides" not in data:
            raise ValueError("Missing 'slides' key in blueprint JSON")
        
        skeleton_slides = []
        for i, s in enumerate(data.get("slides", [])):
            # Handle both key_points and content_description formats
            bullet_points = s.get("key_points", [])
            if not bullet_points and "content_description" in s:
                bullet_points = [s["content_description"]]
            
            skeleton_slides.append(SkeletonSlide(
                order=s.get("order", i + 1),
                title=s.get("title", f"Slide {i + 1}"),
                content_type=s.get("content_type", "content"),
                bullet_points=bullet_points,
                equation_latex=s.get("equation_latex"),
                speaker_notes_hint=s.get("speaker_notes"),
            ))
        
        return Skeleton(
            presentation_title=data.get("title", session.get("topic", "Presentation")),
            target_audience=data.get("target_audience", "Academic"),
            slides=skeleton_slides,
        )
        
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Failed to parse blueprint, using fallback: {e}")
        # Return minimal fallback skeleton
        return Skeleton(
            presentation_title=session.get("topic", "Presentation"),
            target_audience="Academic",
            slides=[
                SkeletonSlide(order=1, title="Title", content_type="title", bullet_points=[session.get("topic", "Presentation")]),
                SkeletonSlide(order=2, title="Content", content_type="content", bullet_points=["Content"]),
            ],
        )


sessions: Dict[str, Dict[str, Any]] = load_sessions()


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/sessions")
async def get_all_sessions():
    """Get all recorded sessions (history)."""
    # Sort by recent first (if we had timestamps, for now just reverse dict)
    return list(sessions.values())[::-1]

@router.post("/start", response_model=StartGenerationResponse)
async def start_generation(
    request: StartGenerationRequest,
    settings: Settings = Depends(get_settings)
) -> StartGenerationResponse:
    """
    Start a new slide generation session.
    
    This initiates the "One-Shot Protocol":
    1. Analyze the mode and input
    2. Generate initial clarification questions
    3. Return session ID for subsequent interactions
    """
    if not settings.gemini_api_key:
        raise HTTPException(
            status_code=503,
            detail="Gemini API key not configured. Please set GEMINI_API_KEY."
        )
    
    # Create session
    session_id = str(uuid.uuid4())
    
    # Initialize Gemini client
    client = GeminiInteractionsClient(api_key=settings.gemini_api_key)
    
    # Resolve System Instruction (from prompts.py, with optional overrides)
    system_instruction = prompts.get_prompt("CLARIFIER_SYSTEM", request.prompt_overrides)

    # Prepare the initial prompt based on mode
    if request.mode == GenerationMode.DEEP_RESEARCH:
        if not request.topic:
            raise HTTPException(
                status_code=400,
                detail="Topic is required for deep research mode"
            )
        base_tmpl = prompts.get_prompt("DEEP_RESEARCH_INITIAL", request.prompt_overrides)
        initial_prompt = base_tmpl.format(system_instruction=system_instruction, topic=request.topic)
    
    elif request.mode == GenerationMode.SYNTHESIS:
        base_tmpl = prompts.get_prompt("SYNTHESIS_INITIAL", request.prompt_overrides)
        initial_prompt = base_tmpl.format(system_instruction=system_instruction)
    
    else:  # REPLICA mode
        base_tmpl = prompts.get_prompt("REPLICA_INITIAL", request.prompt_overrides)
        initial_prompt = base_tmpl.format(system_instruction=system_instruction)

    try:
        # Start metrics tracking for clarifier
        tracker = get_metrics_tracker()
        metric = tracker.start(
            agent_name="clarifier_start",
            model=settings.model_flash,
            thinking_level="none",
            raw_input=initial_prompt,
        )
        
        # Create the interaction
        result = await client.create_interaction(
            prompt=initial_prompt,
            model=settings.model_flash,
        )
        
        # Record tokens for cost tracking
        tokens = result.get("tokens", {})
        tracker.record_tokens(
            metric,
            input_tokens=tokens.get("input_tokens", 0),
            output_tokens=tokens.get("output_tokens", 0),
            thinking_tokens=tokens.get("thinking_tokens", 0),
            cached_tokens=tokens.get("cached_tokens", 0),
        )
        tracker.record_output(metric, raw_output=result.get("response", ""))
        tracker.complete(metric, success=True)
        
        # Store session state
        sessions[session_id] = {
            "mode": request.mode.value,
            "interaction_id": result.get("interaction_id"),
            "state": "clarifying",
            "clarification_count": 0,
            "topic": request.topic,
            "university_profile": request.university_profile,
            "project_id": request.project_id,
            "blueprint": None,
            "prompt_overrides": request.prompt_overrides,
            "history": [
                {
                    "role": "system", 
                    "content": "Session Started",
                    "initial_prompt": initial_prompt
                },
                {
                    "role": "assistant",
                    "content": result.get("response")
                }
            ]
        }
        save_sessions()
        
        return StartGenerationResponse(
            session_id=session_id,
            interaction_id=result.get("interaction_id"),
            status="clarifying",
            clarification_question=result.get("response"),
            message="Session started. Please answer the clarification questions.",
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start generation: {str(e)}"
        )


@router.post("/clarify", response_model=ClarifyResponse)
async def submit_clarification(
    request: ClarifyRequest,
    settings: Settings = Depends(get_settings)
) -> ClarifyResponse:
    """
    Submit an answer to a clarification question.
    
    The system will either:
    - Ask another question if more clarity is needed
    - Generate a blueprint if sufficient information is gathered
    """
    try:
        session = sessions.get(request.session_id)
        if not session:
            print(f"Session {request.session_id} not found")
            raise HTTPException(status_code=404, detail="Session not found")
        
        if session["state"] not in ["clarifying", "blueprint_ready"]:
            print(f"Session {request.session_id} in {session['state']} state")
            raise HTTPException(
                status_code=400,
                detail=f"Session is in state '{session['state']}'"
            )
        
        print(f"Submitting interaction for session {request.session_id} (State: {session['state']})...")
        client = GeminiInteractionsClient(api_key=settings.gemini_api_key)
        tracker = get_metrics_tracker()
        
        # Retrieve overrides from session
        overrides = session.get("prompt_overrides")

        # CASE 1: Blueprint Revision (User wants to change the generated blueprint)
        if session["state"] == "blueprint_ready":
            print("Processing blueprint revision request...")
            
            base_tmpl = prompts.get_prompt("BLUEPRINT_REVISION", overrides)
            revision_prompt = base_tmpl.format(
                current_blueprint=session.get('blueprint_raw', 'No blueprint found'),
                user_request=request.answer
            )

            # Debug logging
            print(f"--- REVISION PROMPT ---\n{revision_prompt}\n-----------------------")

            metric = tracker.start(
                agent_name="blueprint_reviser",
                model=settings.model_pro,
                thinking_level="none",
                raw_input=revision_prompt,
            )

            result = await client.continue_interaction(
                interaction_id=session["interaction_id"],
                prompt=revision_prompt,
                model=settings.model_pro,
            )
            
            raw_response = result.get("response", "")
            print(f"--- REVISION RESPONSE ---\n{raw_response}\n-------------------------")
            
            tracker.record_output(metric, raw_output=raw_response)
            tracker.complete(metric, success=True)
            
            # Update interaction ID to maintain state
            new_id = result.get("interaction_id")
            if new_id and new_id != session["interaction_id"]:
                print(f"Updating interaction ID (Revision): {session['interaction_id']} -> {new_id}")
                session["interaction_id"] = new_id

            # Update session with new blueprint
            session["blueprint_raw"] = raw_response
            save_sessions()
            
            return ClarifyResponse(
                session_id=request.session_id,
                status="blueprint_ready",
                next_question=None,
                blueprint_ready=True,
                message="Blueprint updated based on your feedback.",
            )

        # ... (CASE 2 Clarification Loop)
        # Log user answer
        session.setdefault("history", []).append({
            "role": "user",
            "content": request.answer,
            "timestamp": str(uuid.uuid4()) # rudimentary timestamp
        })

        # Continue clarification interaction first to get AI's reaction
        print("Continuing clarification (with thinking)...")
        metric = tracker.start(
            agent_name="clarifier_continue",
            model=settings.model_flash,
            thinking_level="low",
            raw_input=request.answer,
        )
        
        # Retrieve system instruction from overrides or defaults
        system_instruction = prompts.get_prompt("CLARIFIER_SYSTEM", overrides)
        
        # Use `generate_chat_with_thinking` for FULL observability
        # This sends the full history each turn (trades tokens for thinking visibility)
        result = await client.generate_chat_with_thinking(
            history=session.get("history", []),
            system_instruction=system_instruction,
            model=settings.model_flash,
            thinking_level="low",
        )

        # Log AI Response
        ai_response = result.get("response", "")
        thinking_trace = result.get("thinking", "")
        
        # Update history with AI response
        session["history"].append({
            "role": "assistant",
            "content": ai_response
        })
        
        # Increment count
        session["clarification_count"] = session.get("clarification_count", 0) + 1
        
        tracker.record_output(metric, raw_output=ai_response)
        tracker.complete(metric, success=True)
        
        # CHECK FOR COMPLETION: Either hard limit reached OR Agent signaled completion
        # Use a flexible check for the completion phrase
        is_agent_satisfied = "Great, I have everything I need" in ai_response
        hard_limit_reached = session["clarification_count"] >= 4  # Bumped to 4 to allow 3 full Q&A pairs + closing

        if is_agent_satisfied or hard_limit_reached:
            print(f"Generating blueprint (Satisfied: {is_agent_satisfied}, Limit: {hard_limit_reached})...")
            
            blueprint_prompt = prompts.get_prompt("BLUEPRINT_GENERATION", overrides)
    
            # Track blueprint generation (Metric)
            metric_bp = tracker.start(
                agent_name="clarifier_blueprint",
                model=settings.model_pro,
                thinking_level="none",
                raw_input=blueprint_prompt,
            )
    
            # We pass the blueprint prompt to the SAME interaction context
            # The context already contains the "Great..." message from the agent.
            # We just nudge it to output the JSON now.
            
            bp_result = await client.continue_interaction(
                interaction_id=session["interaction_id"],
                prompt=blueprint_prompt,
                model=settings.model_pro,
            )

            # Update ID again if changed
            new_id_bp = bp_result.get("interaction_id")
            if new_id_bp and new_id_bp != session["interaction_id"]:
                session["interaction_id"] = new_id_bp

            # Log system generation
            session["history"].append({
                "role": "system",
                "content": "Blueprint Generated",
                "raw_response": bp_result.get("response")
            })
            
            tracker.record_output(metric_bp, raw_output=bp_result.get("response", ""))
            tracker.complete(metric_bp, success=True)

            session["state"] = "blueprint_ready"
            session["blueprint_raw"] = bp_result.get("response")
            save_sessions()
            
            return ClarifyResponse(
                session_id=request.session_id,
                status="blueprint_ready",
                next_question=None,
                blueprint_ready=True,
                # Send the "Great..." message as the final message to user before switching
                message=ai_response if is_agent_satisfied else "Blueprint generated! Use GET /api/generate/blueprint to review.",
                thinking=thinking_trace,
            )
        
        save_sessions()
        
        return ClarifyResponse(
            session_id=request.session_id,
            status="clarifying",
            next_question=ai_response,
            blueprint_ready=False,
            message=ai_response, # Use actual response as message
            thinking=thinking_trace,
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in submit_clarification: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clarify/stream")
async def submit_clarification_stream(
    request: ClarifyRequest,
    settings: Settings = Depends(get_settings),
):
    """
    Submit a clarification answer and stream the response.
    
    Uses Server-Sent Events (SSE) to stream thinking and content in real-time.
    Events:
    - event: thinking\ndata: {"text": "<chunk>"}\n\n
    - event: content\ndata: {"text": "<chunk>"}\n\n
    - event: done\ndata: {"thinking": ..., "content": ..., "tokens": ...}\n\n
    """
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    client = GeminiInteractionsClient(api_key=settings.gemini_api_key)
    overrides = session.get("prompt_overrides", {})
    
    # Add user message to history
    session.setdefault("history", []).append({
        "role": "user",
        "content": request.answer,
    })
    
    system_instruction = prompts.get_prompt("CLARIFIER_SYSTEM", overrides)
    
    async def event_generator():
        """Async generator for SSE events."""
        accumulated_content = ""
        accumulated_thinking = ""
        
        async for event in client.generate_chat_with_thinking_stream(
            history=session.get("history", []),
            system_instruction=system_instruction,
            model=settings.model_flash,
            thinking_level="low",
        ):
            yield event
            
            # Parse done event to update session and check for completion
            if event.startswith("event: done"):
                import json
                data_line = event.split("data: ")[1].strip()
                data = json.loads(data_line)
                accumulated_content = data.get("content", "")
                accumulated_thinking = data.get("thinking", "")
                
                # Update session history
                session["history"].append({
                    "role": "assistant",
                    "content": accumulated_content
                })
                session["clarification_count"] = session.get("clarification_count", 0) + 1
                
                # CHECK FOR COMPLETION: Agent signaled it has enough info
                is_agent_satisfied = "Great, I have everything I need" in accumulated_content or \
                                     "I have everything I need" in accumulated_content
                hard_limit_reached = session["clarification_count"] >= 4
                
                if is_agent_satisfied or hard_limit_reached:
                    # Generate blueprint (non-streamed for simplicity)
                    blueprint_prompt = prompts.get_prompt("BLUEPRINT_GENERATION", overrides)
                    
                    # Build history for blueprint generation
                    bp_history = session.get("history", []) + [{
                        "role": "user",
                        "content": blueprint_prompt
                    }]
                    
                    bp_result = await client.generate_chat_with_thinking(
                        history=bp_history,
                        system_instruction=system_instruction,
                        model=settings.model_pro,
                        thinking_level="low",
                    )
                    
                    bp_content = bp_result.get("response", "")
                    session["blueprint_raw"] = bp_content
                    session["state"] = "blueprint_ready"
                    save_sessions()
                    
                    # Send blueprint_ready event
                    yield f"event: blueprint_ready\ndata: {json.dumps({'session_id': request.session_id, 'message': accumulated_content})}\n\n"
                else:
                    save_sessions()
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/blueprint/{session_id}", response_model=BlueprintResponse)
async def get_blueprint(session_id: str) -> BlueprintResponse:
    """
    Get the generated blueprint for review.
    
    The blueprint shows the planned slide structure before generation begins.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session["state"] != "blueprint_ready":
        raise HTTPException(
            status_code=400,
            detail=f"Blueprint not ready. Session state: {session['state']}"
        )
    
    # Parse the blueprint
    raw_content = session.get("blueprint_raw", "")
    
    # Clean Markdown
    cleaned = re.sub(r"```json\s*", "", raw_content)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    
    try:
        data = json.loads(cleaned)
        
        # Validate structure roughly
        if "slides" not in data:
            raise ValueError("Missing 'slides' key in blueprint JSON")
            
        slides = []
        for s in data["slides"]:
            slides.append(BlueprintSlide(
                order=s.get("order", 0),
                title=s.get("title", "Untitled"),
                content_type=s.get("content_type", "content"),
                key_points=[s.get("content_description", "")] if "content_description" in s else s.get("key_points", []),
                has_equation=s.get("needs_equation", False), # AI might hallucinate key, default false
                has_diagram=s.get("needs_diagram", False)
            ))
            
        return BlueprintResponse(
            session_id=session_id,
            title=data.get("title", session.get("topic", "Untitled Presentation")),
            slide_count=len(slides),
            slides=slides,
            estimated_generation_time_seconds=len(slides) * 10, # Estimate 10s per slide
        )
        
    except Exception as e:
        print(f"Failed to parse blueprint: {e}")
        print(f"Raw content: {raw_content}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to parse AI blueprint. Raw output: {raw_content[:200]}..."
        )


@router.post("/approve", response_model=ApproveResponse)
async def approve_blueprint(
    request: ApproveRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings)
) -> ApproveResponse:
    """
    Approve the blueprint and start slide generation.
    
    This triggers the async parallel generation workflow:
    1. Each slide is generated concurrently
    2. Visual QA loop runs per slide (Playwright + Vision)
    3. Results stored with visual scores
    """
    session = sessions.get(request.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    logger.info(f"Approve request for session {request.session_id}, current state: {session.get('state')}")
    
    if session["state"] != "blueprint_ready":
        raise HTTPException(
            status_code=400,
            detail=f"Blueprint must be reviewed before approval. Current state: {session.get('state')}"
        )
    
    # Create generation job
    job_id = str(uuid.uuid4())
    session["state"] = "generating"
    session["job_id"] = job_id
    save_sessions()
    
    # Initialize event queue for this session
    session_events[request.session_id] = asyncio.Queue()
    
    # Run generation in background using the new pipeline
    async def run_generation():
        queue = session_events.get(request.session_id)
        try:
            # Emit pipeline start
            if queue:
                await queue.put({
                    "type": "pipeline_start",
                    "session_id": request.session_id,
                    "job_id": job_id
                })
            
            # Build skeleton from actual blueprint (parsed from clarifier stage)
            skeleton = parse_blueprint_to_skeleton(session)
            logger.info(f"Parsed skeleton with {len(skeleton.slides)} slides from blueprint")
            
            # Import OrderForm for the pipeline
            from app.agents.clarifier import OrderForm
            
            # Create order form using actual slide count from blueprint
            order_form = OrderForm(
                theme_id="modern",
                citation_style="apa",
                tone="academic",
                target_audience=skeleton.target_audience,
                target_slides=len(skeleton.slides),
                presentation_title=skeleton.presentation_title,
            )
            
            pipeline = SlideGenerationPipeline(api_key=settings.gemini_api_key)
            result = await pipeline.generate_from_skeleton(skeleton, order_form, event_queue=queue)
            
            session["generation_result"] = result.model_dump()
            session["state"] = "completed" if result.success else "failed"
            session["average_visual_score"] = result.average_visual_score
            save_sessions()
            
            # Emit pipeline complete
            if queue:
                await queue.put({
                    "type": "pipeline_complete",
                    "session_id": request.session_id,
                    "success": result.success,
                    "average_visual_score": result.average_visual_score
                })
            
        except Exception as e:
            logger.error(f"Generation pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            session["state"] = "failed"
            session["error"] = str(e)
            save_sessions()
            
            # Emit error
            if queue:
                await queue.put({
                    "type": "pipeline_error",
                    "session_id": request.session_id,
                    "message": str(e)
                })
    
    # Add to background tasks
    background_tasks.add_task(run_generation)
    
    return ApproveResponse(
        session_id=request.session_id,
        status="generating",
        message="Generation started! Slides are being generated in parallel with Visual QA.",
        generation_job_id=job_id,
    )


@router.get("/status/{session_id}")
async def get_generation_status(session_id: str):
    """
    Get current generation status.
    
    Returns the state, progress, and visual scores of a generation session.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    response = {
        "session_id": session_id,
        "state": session["state"],
        "mode": session["mode"],
        "job_id": session.get("job_id"),
        "clarification_count": session.get("clarification_count", 0),
    }
    
    # Add visual score if generation completed
    if "average_visual_score" in session:
        response["average_visual_score"] = session["average_visual_score"]
        response["visual_score_display"] = f"{session['average_visual_score']:.0%}"
    
    # Add error if failed
    if session.get("error"):
        response["error"] = session["error"]
    
    return response


@router.get("/result/{session_id}")
async def get_generation_result(session_id: str):
    """
    Get the full generation result including all slides.
    
    Only available after generation is complete.
    """
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if session["state"] != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Generation not complete. Current state: {session['state']}"
        )
    
    result = session.get("generation_result", {})
    
    return {
        "session_id": session_id,
        "success": result.get("success", False),
        "average_visual_score": result.get("average_visual_score", 0),
        "visual_score_display": f"{result.get('average_visual_score', 0):.0%}",
        "slides": result.get("slides", []),
        "pptx_url": result.get("pptx_url"),
    }


# =============================================================================
# Event Streaming (SSE)
# =============================================================================

# Global event queues for generation sessions
# session_id -> asyncio.Queue
session_events: Dict[str, asyncio.Queue] = {}


@router.get("/events/{session_id}")
async def stream_generation_events(session_id: str):
    """
    Stream real-time events from the generation pipeline.
    
    Events:
    - start: {agent: "name"}
    - thinking: {agent: "name", text: "chunk"}
    - complete: {agent: "name", stats: {...}}
    - error: {message: "..."}
    """
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]
    
    # Check if generation is complete - no need to stream
    if session.get("state") == "completed":
        # Return the completion event directly
        async def completed_generator():
            yield f'event: pipeline_complete\ndata: {json.dumps({"type": "pipeline_complete", "session_id": session_id, "success": True, "average_visual_score": session.get("average_visual_score", 0)})}\n\n'
        return StreamingResponse(
            completed_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        )
    
    if session.get("state") == "failed":
        async def error_generator():
            yield f'event: pipeline_error\ndata: {json.dumps({"type": "pipeline_error", "session_id": session_id, "message": session.get("error", "Unknown error")})}\n\n'
        return StreamingResponse(
            error_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        )

    # Don't create a new queue on reconnect! Use existing queue from active generation
    if session_id not in session_events:
        # No active generation - client connected too early or pipeline hasn't started
        async def waiting_generator():
            yield f'event: waiting\ndata: {json.dumps({"type": "waiting", "message": "Waiting for generation to start..."})}\n\n'
            # Keep connection alive and wait for queue to appear
            for _ in range(60):  # Wait up to 60 seconds
                await asyncio.sleep(1)
                if session_id in session_events:
                    # Queue appeared, switch to it
                    queue = session_events[session_id]
                    try:
                        while True:
                            event = await asyncio.wait_for(queue.get(), timeout=30)
                            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                            if event['type'] in ('pipeline_complete', 'pipeline_error'):
                                break
                    except asyncio.TimeoutError:
                        yield f'event: timeout\ndata: {json.dumps({"type": "timeout", "message": "No events received"})}\n\n'
                    return
            yield f'event: timeout\ndata: {json.dumps({"type": "timeout", "message": "Generation did not start"})}\n\n'
        return StreamingResponse(
            waiting_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"}
        )

    async def event_generator():
        queue = session_events[session_id]
        try:
            while True:
                # Wait for next event with timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30)
                except asyncio.TimeoutError:
                    # Send keepalive
                    yield f": keepalive\n\n"
                    continue
                
                # Yield SSE format
                try:
                    # Debug: Log event emission
                    if event['type'] in ['thinking', 'start', 'complete', 'qa_iteration', 'pipeline_complete', 'pipeline_error']:
                        logger.info(f"SSE emit [{session_id[:8]}]: {event['type']} - {event.get('agent', 'pipeline')}") 
                    yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    # Client disconnected - exit gracefully
                    logger.debug(f"Client disconnected during event send: {session_id}")
                    break
                
                # Check for final event
                if event['type'] == 'pipeline_complete' or event['type'] == 'pipeline_error':
                    break
        except asyncio.CancelledError:
            # Client disconnected - this is normal
            logger.debug(f"SSE cancelled for session: {session_id}")
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Client disconnected - exit gracefully
            logger.debug(f"Client disconnected: {session_id}")
        except Exception as e:
            # Log unexpected errors but don't crash
            logger.warning(f"SSE error for {session_id}: {e}")

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ============================================================================
# Playground Endpoints (For Agent Optimization)
# ============================================================================

CUSTOM_PROMPTS_FILE = "custom_prompts.json"


def load_custom_prompts() -> Dict[str, str]:
    """Load custom prompts from file."""
    if os.path.exists(CUSTOM_PROMPTS_FILE):
        try:
            with open(CUSTOM_PROMPTS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Failed to load custom prompts: {e}")
            return {}
    return {}


def save_custom_prompts(prompts_dict: Dict[str, str]):
    """Save custom prompts to file."""
    try:
        with open(CUSTOM_PROMPTS_FILE, "w") as f:
            json.dump(prompts_dict, f, indent=2)
    except Exception as e:
        print(f"Failed to save custom prompts: {e}")


@router.get("/prompts")
async def get_all_prompts():
    """
    Get all default prompts for the Playground UI.
    """
    return prompts.DEFAULT_PROMPTS


@router.get("/prompts/custom")
async def get_custom_prompts():
    """
    Get user's custom/edited prompts for the Playground UI.
    
    Returns empty dict if no custom prompts saved.
    """
    return load_custom_prompts()


class SavePromptsRequest(BaseModel):
    """Request body for saving custom prompts."""
    prompts: Dict[str, str] = Field(..., description="Dictionary of prompt key -> prompt text")


@router.post("/prompts/save")
async def save_user_prompts(request: SavePromptsRequest):
    """
    Save custom prompts for the Playground UI.
    
    Persists the user's edited prompts to a local file.
    These can be loaded with GET /prompts/custom.
    """
    save_custom_prompts(request.prompts)
    return {
        "status": "saved",
        "message": f"Saved {len(request.prompts)} custom prompts",
        "prompts_saved": list(request.prompts.keys())
    }


@router.delete("/prompts/custom")
async def reset_custom_prompts():
    """
    Reset custom prompts back to defaults.
    
    Deletes the custom prompts file.
    """
    if os.path.exists(CUSTOM_PROMPTS_FILE):
        os.remove(CUSTOM_PROMPTS_FILE)
    return {"status": "reset", "message": "Custom prompts cleared"}


class InitialMessageConfig(BaseModel):
    """Configuration for custom initial message."""
    initial_message: Optional[str] = Field(
        None, 
        description="Custom initial message for the clarifier agent. If null, uses default."
    )


@router.post("/config/initial-message")
async def set_initial_message(config: InitialMessageConfig):
    """
    Set a custom initial message for new sessions.
    
    This message will be used as the first clarifier question
    instead of the AI-generated one.
    """
    # Store in a simple config file
    config_file = "playground_config.json"
    try:
        existing = {}
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                existing = json.load(f)
        
        existing["initial_message"] = config.initial_message
        
        with open(config_file, "w") as f:
            json.dump(existing, f, indent=2)
        
        return {
            "status": "saved",
            "message": "Initial message saved" if config.initial_message else "Initial message cleared"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save config: {e}")


@router.get("/config/initial-message")
async def get_initial_message():
    """
    Get the custom initial message configuration.
    
    Returns null if using default.
    """
    config_file = "playground_config.json"
    try:
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                config = json.load(f)
            return {"initial_message": config.get("initial_message")}
        return {"initial_message": None}
    except Exception as e:
        return {"initial_message": None}

