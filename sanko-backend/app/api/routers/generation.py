"""
Generation API Router - Production Ready

Endpoints that interface with the SlideGenerationFlow.
Supports:
- Multi-turn clarification
- Outline review and modification
- SSE streaming of generation progress
- Session management with database persistence
- R2 cloud storage for PDF uploads with content-hash caching
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime
import json
import asyncio
import os
from pathlib import Path
import threading

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
from app.core.database import get_db
from app.services.storage import get_storage_service, PDFCacheService
from app.services.convex_service import get_convex_service

logger = get_logger(__name__)

router = APIRouter(prefix="/generation", tags=["generation"])


# =============================================================================
# Thread-Safe In-Memory Session Store
# =============================================================================

_sessions: Dict[str, FlowState] = {}
_sessions_lock = threading.RLock()  # Thread-safe lock for session access


def get_session(session_id: str) -> FlowState:
    """Get session from store (thread-safe)."""
    with _sessions_lock:
        if session_id not in _sessions:
            raise HTTPException(status_code=404, detail="Session not found")
        return _sessions[session_id]


def save_session(state: FlowState):
    """Save session to store (thread-safe)."""
    with _sessions_lock:
        _sessions[state.session_id] = state


# =============================================================================
# Background Processing Status Tracker
# =============================================================================

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

class ProcessingStatus(str, Enum):
    """Status of PDF synthesis processing."""
    QUEUED = "queued"        # Waiting to start
    PROCESSING = "processing"  # Gemini is extracting content
    COMPLETED = "completed"   # Successfully cached
    FAILED = "failed"         # Synthesis failed


@dataclass
class ProcessingJob:
    """Tracks a background synthesis job."""
    file_hash: str
    filename: str
    r2_key: str
    status: ProcessingStatus = ProcessingStatus.QUEUED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    sections_count: Optional[int] = None


# In-memory tracking of processing jobs (keyed by file_hash)
_processing_jobs: Dict[str, ProcessingJob] = {}
_processing_lock = threading.RLock()


def get_processing_status(file_hash: str) -> Optional[ProcessingJob]:
    """Get the processing status for a file hash."""
    with _processing_lock:
        return _processing_jobs.get(file_hash)


def set_processing_status(job: ProcessingJob):
    """Update the processing status for a file."""
    with _processing_lock:
        _processing_jobs[job.file_hash] = job


# =============================================================================
# File Upload Helpers
# =============================================================================

ALLOWED_CONTENT_TYPES = {"application/pdf"}
MAX_FILE_SIZE_MB = 50


def validate_upload_file(file: UploadFile) -> None:
    """Validate uploaded file is a PDF and within size limits."""
    # Check content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only PDF files are allowed."
        )
    
    # Check filename extension as fallback
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=400,
            detail="Invalid file extension. Only .pdf files are allowed."
        )


# =============================================================================
# Request/Response Models
# =============================================================================

class StartSessionResponse(BaseModel):
    """Response when starting a new session."""
    session_id: str
    status: str
    message: str
    files_uploaded: Optional[int] = None
    cache_hits: Optional[int] = None  # Number of files with cached KnowledgeBase


class ClarifyRequest(BaseModel):
    """Request to continue clarification."""
    message: str
    file_hashes: Optional[List[str]] = None  # NEW: Hashes of attached files to process


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


class FileUploadResult(BaseModel):
    """Result for a single uploaded file."""
    file_hash: str
    filename: str
    size_bytes: int
    r2_key: str
    cached: bool  # True if KnowledgeBase already in cache
    sections_count: Optional[int] = None  # If cached, how many sections


class FileUploadResponse(BaseModel):
    """Response from file upload endpoint."""
    files: List[FileUploadResult]
    total_cached: int
    message: str


class OutlineResponse(BaseModel):
    """Response containing the outline."""
    session_id: str
    status: str
    skeleton: Dict


class ApproveRequest(BaseModel):
    """Request to approve/modify outline."""
    modifications: Optional[List[Dict]] = None
    modified_skeleton: Optional[Dict] = None  # Full skeleton replacement


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
async def start_session_endpoint(
    project_id: Optional[str] = None,
    mode: Optional[str] = None,
    topic: Optional[str] = None,
    files: Optional[List[UploadFile]] = File(None),
):
    """
    Start a new generation session.
    
    Args:
        project_id: Optional link to an existing project for history tracking
        mode: Generation mode - "deep_research", "synthesis", or "replica"
        topic: Initial topic for deep research mode
        files: Optional PDF files for synthesis mode
    
    Returns a session_id to use for subsequent calls.
    Begins in AWAITING_CLARIFICATION status (or SYNTHESIZING if files are provided).
    
    Files are uploaded to R2 cloud storage with content-hash deduplication.
    """
    state = await create_session(project_id=project_id, mode=mode, topic=topic)
    save_session(state)
    
    # If files are provided, upload to R2 and run synthesis
    if files:
        logger.info(f"Received {len(files)} files for synthesis. Starting session {state.session_id}")
        
        storage = get_storage_service()
        cache_service = PDFCacheService()
        
        # Track uploaded files and cache hits
        uploaded_files = []
        cache_hits = 0
        
        # Get Convex client for cache lookups
        client = get_db()
        
        # We process files directly
        for file in files:
                # Validate file
                validate_upload_file(file)
                
                # Read file content
                file_data = await file.read()
                
                # Upload to R2 (with deduplication)
                file_hash, r2_key, was_duplicate = await storage.upload_file(
                    file_data=file_data,
                    original_filename=file.filename,
                    content_type=file.content_type or "application/pdf",
                )
                
                # Check cache for existing KnowledgeBase
                # TODO: Implement Convex cache lookup
                # cached_kb = await cache_service.get_cached(file_hash, client)
                cached_kb = None 
                if cached_kb:
                    cache_hits += 1
                
                uploaded_files.append({
                    "file_hash": file_hash,
                    "r2_key": r2_key,
                    "filename": file.filename,
                    "size_bytes": len(file_data),
                    "cached": cached_kb is not None,
                })
        
        # Store file info in state for synthesis
        state.uploaded_files = uploaded_files
        
        # Run synthesis with R2 keys
        flow = SlideGenerationFlow(session_id=state.session_id)
        flow.state = state
        await flow.run_synthesis_from_r2(uploaded_files)
        save_session(state)
        
        return StartSessionResponse(
            session_id=state.session_id,
            status=state.status,
            message=f"Session created. {len(files)} files processed ({cache_hits} from cache).",
            files_uploaded=len(files),
            cache_hits=cache_hits,
        )
    
    return StartSessionResponse(
        session_id=state.session_id,
        status=state.status,
        message="Session created. Send your first message to /clarify/{session_id}",
    )


@router.post("/upload", response_model=FileUploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload PDF files to R2 storage and check cache.
    
    This is Phase 1 of the two-phase upload:
    1. Upload to R2 + check cache (this endpoint)
    2. Process with Gemini on message send (if not cached)
    
    Returns file hash and cache status for each file.
    Frontend should call this as soon as user attaches files.
    
    If a file is not cached, background synthesis is started automatically.
    Frontend can poll /processing-status/{file_hash} to check progress.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    logger.info(f"[UPLOAD] Starting upload for {len(files)} file(s)")
    
    storage = get_storage_service()
    cache_service = PDFCacheService()
    
    results = []
    total_cached = 0
    files_to_process = []  # Files that need background synthesis
    
    # async for db_session in get_async_session():
    # client = get_db()
    
    # Just run once
    for file in files:
        logger.info(f"[UPLOAD] Processing file: {file.filename}")
        
        # Validate file
        validate_upload_file(file)
        logger.info(f"[UPLOAD]   ✓ File validation passed")
        
        # Check file size (20MB limit)
        file_data = await file.read()
        file_size_mb = len(file_data) / 1024 / 1024
        logger.info(f"[UPLOAD]   File size: {file_size_mb:.2f}MB")
        
        if len(file_data) > 20 * 1024 * 1024:  # 20MB
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' exceeds 20MB limit ({file_size_mb:.1f}MB)"
            )
        
        # Upload to R2 (with deduplication)
        logger.info(f"[UPLOAD]   Uploading to R2...")
        file_hash, r2_key, was_duplicate = await storage.upload_file(
            file_data=file_data,
            original_filename=file.filename,
            content_type=file.content_type or "application/pdf",
        )
        logger.info(f"[UPLOAD]   ✓ R2 upload complete: hash={file_hash[:16]}... (duplicate={was_duplicate})")
        
        # Check cache for existing KnowledgeBase (this means Gemini has already processed it)
        logger.info(f"[UPLOAD]   Checking if Gemini has processed this PDF...")
        # TODO: Implement Convex cache lookup
        cached_kb = None # await cache_service.get_cached(file_hash, get_db())
        is_cached = cached_kb is not None
        sections_count = len(cached_kb.sections) if cached_kb else None
        
        # Check if already being processed
        existing_job = get_processing_status(file_hash)
        is_processing = existing_job and existing_job.status in [ProcessingStatus.QUEUED, ProcessingStatus.PROCESSING]
        
        if is_cached:
            total_cached += 1
            logger.info(f"[UPLOAD]   ✓ CACHE HIT: Gemini already processed - {sections_count} sections extracted")
        elif is_processing:
            logger.info(f"[UPLOAD]   ⏳ Already processing in background")
        else:
            # Queue for background processing
            logger.info(f"[UPLOAD]   🚀 Queuing for background synthesis")
            files_to_process.append({
                "file_hash": file_hash,
                "r2_key": r2_key,
                "filename": file.filename,
            })
            # Create job tracker
            job = ProcessingJob(
                file_hash=file_hash,
                filename=file.filename,
                r2_key=r2_key,
                status=ProcessingStatus.QUEUED,
            )
            set_processing_status(job)
        
        results.append(FileUploadResult(
            file_hash=file_hash,
            filename=file.filename,
            size_bytes=len(file_data),
            r2_key=r2_key,
            cached=is_cached,
            sections_count=sections_count,
        ))
    
    # Start background synthesis for uncached files
    if files_to_process:
        logger.info(f"[UPLOAD] Starting background synthesis for {len(files_to_process)} file(s)")
        for file_info in files_to_process:
            asyncio.create_task(_run_background_synthesis(file_info))
    
    logger.info(f"[UPLOAD] Complete: {len(results)} file(s), {total_cached} cached, {len(files_to_process)} queued for processing")
    
    return FileUploadResponse(
        files=results,
        total_cached=total_cached,
        message=f"{len(results)} file(s) uploaded. {total_cached} cached, {len(files_to_process)} processing.",
    )


async def _run_background_synthesis(file_info: Dict[str, str]):
    """
    Run synthesis in background for a single file.
    Updates the ProcessingJob status throughout.
    """
    file_hash = file_info["file_hash"]
    r2_key = file_info["r2_key"]
    filename = file_info["filename"]
    
    logger.info(f"[BG-SYNTHESIS] Starting for {filename} ({file_hash[:16]}...)")
    
    # Update status to processing
    job = ProcessingJob(
        file_hash=file_hash,
        filename=filename,
        r2_key=r2_key,
        status=ProcessingStatus.PROCESSING,
        started_at=datetime.now(),
    )
    set_processing_status(job)
    
    try:
        # Create a temporary flow just for synthesis
        from app.crew.flows.slide_generation import SlideGenerationFlow
        
        flow = SlideGenerationFlow(session_id=f"bg-{file_hash[:16]}")
        await flow.run_synthesis_from_r2([{
            "file_hash": file_hash,
            "r2_key": r2_key,
            "filename": filename,
        }])
        
        # Check if synthesis succeeded
        if flow.state.knowledge_base and flow.state.knowledge_base.sections:
            sections_count = len(flow.state.knowledge_base.sections)
            job.status = ProcessingStatus.COMPLETED
            job.sections_count = sections_count
            job.completed_at = datetime.now()
            logger.info(f"[BG-SYNTHESIS] ✓ Completed {filename}: {sections_count} sections")
        elif flow.state.failure_context:
            failures = flow.state.failure_context.get("failed_synthesis", [])
            error_msg = failures[0].get("error", "Unknown error") if failures else "Unknown error"
            job.status = ProcessingStatus.FAILED
            job.error_message = error_msg
            job.completed_at = datetime.now()
            logger.error(f"[BG-SYNTHESIS] ✗ Failed {filename}: {error_msg}")
        else:
            job.status = ProcessingStatus.FAILED
            job.error_message = "No content extracted"
            job.completed_at = datetime.now()
            logger.error(f"[BG-SYNTHESIS] ✗ Failed {filename}: No content extracted")
            
    except Exception as e:
        logger.error(f"[BG-SYNTHESIS] ✗ Exception for {filename}: {e}")
        job.status = ProcessingStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.now()
    
    set_processing_status(job)


@router.get("/processing-status/{file_hash}")
async def get_file_processing_status(file_hash: str):
    """
    Get the processing status for a specific file.
    
    Frontend can poll this while waiting for synthesis to complete.
    """
    job = get_processing_status(file_hash)
    
    if not job:
        # Check if it's already cached
        cache_service = PDFCacheService()
        try:
            # TODO: Convex cache lookup
            # async for db_session in get_async_session():
            #    cached_kb = await cache_service.get_cached(file_hash, db_session)
            cached_kb = None
            if cached_kb:
                return {
                    "file_hash": file_hash,
                    "status": "completed",
                    "cached": True,
                    "sections_count": len(cached_kb.sections),
                }
        except Exception:
            pass
        
        raise HTTPException(
            status_code=404,
            detail="No processing job found for this file hash"
        )
    
    return {
        "file_hash": job.file_hash,
        "filename": job.filename,
        "status": job.status.value,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "sections_count": job.sections_count,
        "error_message": job.error_message,
    }


@router.post("/clarify/{session_id}", response_model=ClarifyResponse)
async def clarify_session(session_id: str, request: ClarifyRequest):
    """
    Continue the clarification conversation.
    
    Send user messages here until the OrderForm is complete.
    The agent will ask follow-up questions until it has enough info.
    
    If file_hashes are provided, process any uncached PDFs before responding.
    This enables mid-chat PDF uploads with immediate integration.
    
    When complete=True, proceed to /outline/{session_id}
    """
    state = get_session(session_id)
    
    if state.status not in [FlowStatus.AWAITING_CLARIFICATION, "awaiting_clarification"]:
        raise HTTPException(
            status_code=400,
            detail=f"Session not in clarification phase. Status: {state.status}",
        )
    
    try:
        # Process any new file attachments before agent response
        new_files_processed = 0
        synthesis_failures = []
        
        if request.file_hashes:
            logger.info(f"[CLARIFY] Processing {len(request.file_hashes)} attached file(s)")
            storage = get_storage_service()
            cache_service = PDFCacheService()
            
            for file_hash in request.file_hashes:
                logger.info(f"[CLARIFY] Checking file hash: {file_hash[:16]}...")
                
                # Check if already in session's uploaded_files
                existing_hashes = {f.get("file_hash") for f in state.uploaded_files}
                if file_hash in existing_hashes:
                    logger.info(f"[CLARIFY]  ⏭ Already in session, skipping")
                    continue  # Already processed
                
                # Check cache first (quick separate DB session)
                logger.info(f"[CLARIFY]   Checking if Gemini has processed this PDF...")
                cached_kb = None
                try:
                    # TODO: Convex cache lookup
                    # async for db_session in get_async_session():
                    #     cached_kb = await cache_service.get_cached(file_hash, db_session)
                    #     break
                    pass
                except Exception as e:
                    logger.warning(f"[CLARIFY]   Cache check failed: {e}")
                
                if cached_kb:
                    # Merge cached KB into session
                    logger.info(f"[CLARIFY]   ✓ CACHE HIT: Using pre-processed KnowledgeBase ({len(cached_kb.sections)} sections)")
                    if state.knowledge_base:
                        state.knowledge_base.sections.extend(cached_kb.sections)
                        state.knowledge_base.summary += f"\n\n{cached_kb.summary}"
                    else:
                        state.knowledge_base = cached_kb
                    new_files_processed += 1
                else:
                    # Need to process with Gemini - find R2 key
                    logger.info(f"[CLARIFY]  CACHE MISS: Need to process with Gemini")
                    
                    # Search R2 for the file (no DB connection needed)
                    r2_key = None
                    logger.info(f"[CLARIFY]  Searching R2 for files with hash {file_hash[:16]}...")
                    try:
                        async with storage._get_client() as client:
                            response = await client.list_objects_v2(
                                Bucket=storage.bucket_name,
                                Prefix=f"uploads/{file_hash}/",
                                MaxKeys=1
                            )
                            contents = response.get("Contents", [])
                            if contents:
                                r2_key = contents[0]["Key"]
                                logger.info(f"[CLARIFY]   ✓ Found R2 file: {r2_key}")
                            else:
                                logger.warning(f"[CLARIFY]  No files found in R2 with hash prefix")
                    except Exception as e:
                        logger.error(f"[CLARIFY]   ✗ Error searching R2: {e}")
                    
                    if r2_key:
                        # Run synthesis (manages its own DB connections now)
                        logger.info(f"[CLARIFY]  Starting Gemini processing for: {r2_key}")
                        try:
                            flow = SlideGenerationFlow(session_id=session_id)
                            flow.state = state
                            await flow.run_synthesis_from_r2([{
                                "file_hash": file_hash,
                                "r2_key": r2_key,
                                "filename": r2_key.split("/")[-1] if "/" in r2_key else "document.pdf",
                            }])
                            
                            # Check if synthesis had failures
                            if state.failure_context and "failed_synthesis" in state.failure_context:
                                synthesis_failures.extend(state.failure_context["failed_synthesis"])
                            else:
                                new_files_processed += 1
                            logger.info(f"[CLARIFY]   ✓ Gemini processing complete")
                        except Exception as e:
                            logger.error(f"[CLARIFY]   ✗ Synthesis failed: {e}")
                            synthesis_failures.append({
                                "filename": r2_key.split("/")[-1] if "/" in r2_key else "document.pdf",
                                "error": str(e)
                            })
                    else:
                        logger.warning(f"[CLARIFY]   ✗ File not found - hash {file_hash[:16]} not in cache or R2")
        
        # Build message with synthesis status
        message = request.message
        if new_files_processed > 0:
            message = f"[SYSTEM NOTE: {new_files_processed} new document(s) have been added to the context. The document content is now available for reference.]\n\nUser message: {message}"
            logger.info(f"[CLARIFY] Injected system note for {new_files_processed} new document(s)")
        
        if synthesis_failures:
            # Add failure notice so agent can inform user
            failure_msg = f"[SYSTEM NOTE: {len(synthesis_failures)} document(s) could not be processed. "
            failure_msg += "The user can paste relevant text content directly as a fallback.]\n\n"
            message = failure_msg + message
            logger.info(f"[CLARIFY] Injected synthesis failure note")
        
        result = await process_clarification(session_id, message, state)
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
        error_str = str(e)
        logger.error(f"Clarification failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Handle rate limit / quota errors
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            # Extract retry delay if available
            retry_delay = 60  # Default
            if "retry in" in error_str.lower():
                import re
                match = re.search(r'retry in (\d+)', error_str.lower())
                if match:
                    retry_delay = int(match.group(1))
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit",
                    "message": "API rate limit exceeded. Please wait before trying again.",
                    "retry_after": retry_delay,
                    "user_message": f"You've hit the API rate limit. Please wait {retry_delay} seconds and try again."
                }
            )
        
        # Handle model not found errors
        if "404" in error_str or "NOT_FOUND" in error_str or "is not found" in error_str:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "model_unavailable",
                    "message": "The AI model is currently unavailable.",
                    "user_message": "The AI service is temporarily unavailable. Please try again later."
                }
            )
        
        # Handle authentication errors
        if "401" in error_str or "UNAUTHENTICATED" in error_str or "api key" in error_str.lower():
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "auth_error",
                    "message": "API authentication failed.",
                    "user_message": "There's an issue with the AI service configuration. Please contact support."
                }
            )
        
        # Generic server error
        raise HTTPException(
            status_code=500, 
            detail={
                "error": "internal_error",
                "message": str(e),
                "user_message": "An unexpected error occurred. Please try again."
            }
        )


@router.post("/confirm/{session_id}", response_model=ClarifyResponse)
async def confirm_clarification(session_id: str, background_tasks: BackgroundTasks):
    """
    Confirm the gathered clarification info.
    
    Called when user clicks "Approve" button on the confirmation UI.
    Finalizes the OrderForm and moves to CLARIFICATION_COMPLETE status.
    
    Automatically triggers background outline generation.
    """
    state = get_session(session_id)
    return await _confirm_clarification_logic(session_id, state, background_tasks)

async def _confirm_clarification_logic(session_id: str, state: FlowState, background_tasks: BackgroundTasks):
    
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
        include_speaker_notes=False,  # Speaker notes not currently supported
        special_requests=state.gathered_info.special_requests or "",
        is_complete=True,
    )
    
    state.order_form = order_form
    state.status = FlowStatus.CLARIFICATION_COMPLETE
    save_session(state)
    
    # TRIGGER OUTLINE GENERATION IN BACKGROUND
    background_tasks.add_task(_run_outline_generation_task, session_id, state)
    
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
        skeleton = await approve_outline(
            session_id, 
            state, 
            request.modifications, 
            request.modified_skeleton
        )
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
    """Background task for generation with Convex progress tracking."""
    convex = get_convex_service()
    project_id = getattr(state, 'project_id', None)
    
    try:
        # Start Convex progress tracking if we have a project ID
        if project_id:
            try:
                await convex.start_generation(project_id, session_id)
            except Exception as e:
                logger.warning(f"[CONVEX] Failed to start progress tracking: {e}")
        
        # Update progress: Generating slides
        if project_id:
            try:
                await convex.update_progress(
                    session_id=session_id,
                    current_step="generating",
                    step_progress=0,
                    total_slides=state.total_slides,
                    message="Starting slide generation..."
                )
            except Exception as e:
                logger.warning(f"[CONVEX] Failed to update progress: {e}")
        
        # Run the actual generation
        await run_generation(session_id, state)
        save_session(state)
        
        # Complete Convex progress tracking
        if project_id:
            try:
                slides_data = None
                if state.generated_presentation:
                    slides_data = state.generated_presentation.model_dump()
                await convex.complete_generation(session_id, slides_data)
            except Exception as e:
                logger.warning(f"[CONVEX] Failed to complete progress: {e}")
        
    except Exception as e:
        error_str = str(e)
        logger.error(f"Generation failed: {e}")
        state.status = FlowStatus.FAILED
        
        # Classify error for user-friendly message
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            state.error_message = "Rate limit exceeded. Please wait a moment and try again."
        elif "404" in error_str or "NOT_FOUND" in error_str:
            state.error_message = "AI model temporarily unavailable. Please try again later."
        elif "401" in error_str or "UNAUTHENTICATED" in error_str:
            state.error_message = "API authentication issue. Please contact support."
        else:
            state.error_message = f"Generation failed: {str(e)[:200]}"
        
        save_session(state)
        
        # Report failure to Convex
        if project_id:
            try:
                await convex.fail_generation(session_id, state.error_message or str(e))
            except Exception as convex_err:
                logger.warning(f"[CONVEX] Failed to report failure: {convex_err}")


async def _run_outline_generation_task(session_id: str, state: FlowState):
    """Background task for outline generation."""
    try:
        logger.info(f"[OUTLINE_TASK] Starting background outline generation for session {session_id}")
        logger.info(f"[OUTLINE_TASK] State BEFORE generate_outline: status={state.status}, skeleton={'SET' if state.skeleton else 'NONE'}")
        
        await generate_outline(session_id, state)
        
        logger.info(f"[OUTLINE_TASK] State AFTER generate_outline: status={state.status}, skeleton={'SET' if state.skeleton else 'NONE'}")
        if state.skeleton:
            logger.info(f"[OUTLINE_TASK] Skeleton has {len(state.skeleton.slides)} slides")
        
        save_session(state)
        logger.info(f"[OUTLINE_TASK] save_session() completed for session {session_id}")
        
        # Sync with Convex
        try:
            if state.project_id:
                convex = get_convex_service()
                logger.info(f"[OUTLINE_TASK] Syncing blueprint to Convex for project {state.project_id}")
                
                # Ensure progress record exists before calling save_outline
                # (save_outline calls updateProgress which requires an existing record)
                try:
                    await convex.start_generation(state.project_id, session_id)
                    logger.info(f"[OUTLINE_TASK] ✅ Started Convex progress tracking")
                except Exception as start_err:
                    logger.warning(f"[OUTLINE_TASK] start_generation failed (may already exist): {start_err}")
                
                # Format skeleton for frontend
                # We reuse the same structure the polling endpoint returns
                if state.skeleton:
                    # We send the whole skeleton model dump
                    await convex.save_outline(session_id, state.skeleton.model_dump())
                    logger.info(f"[OUTLINE_TASK] ✅ Blueprint synced to Convex")
                else:
                    logger.warning("[OUTLINE_TASK] ⚠️ No skeleton to sync")
        except Exception as convex_err:
            logger.error(f"[OUTLINE_TASK] ❌ Convex sync failed: {convex_err}")
            # Non-fatal, frontend can fallback to polling if implemented or just wait
            
        logger.info(f"[OUTLINE_TASK] ✅ Outline generation complete - frontend should now detect skeleton")
    except Exception as e:
        error_str = str(e)
        logger.error(f"[OUTLINE_TASK] ❌ Background outline generation failed: {e}")
        state.status = FlowStatus.FAILED
        
        # Classify error for user-friendly message
        if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "quota" in error_str.lower():
            state.error_message = "Rate limit exceeded. Please wait a moment and try again."
        elif "503" in error_str or "overloaded" in error_str.lower() or "unavailable" in error_str.lower() or "timed out" in error_str.lower():
            state.error_message = "AI service is temporarily overloaded. Please try again in a few minutes."
        elif "404" in error_str or "NOT_FOUND" in error_str:
            state.error_message = "AI model temporarily unavailable. Please try again later."
        elif "401" in error_str or "UNAUTHENTICATED" in error_str:
            state.error_message = "API authentication issue. Please contact support."
        else:
            state.error_message = f"Outline generation failed: {str(e)[:200]}"
        
        save_session(state)


@router.get("/stream/{session_id}")
async def stream_progress(session_id: str):
    """
    Stream generation progress via Server-Sent Events (SSE).
    """
    # Import here to avoid circular dependency
    from app.crew.flows.slide_generation import FlowEventEmitter
    
    # Get or create emitter for this session
    emitter = FlowEventEmitter.get_or_create(session_id)
    
    async def event_generator() -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        
        async def listener(event: Dict):
            await queue.put(event)
            
        emitter.add_listener(listener)
        
        try:
            while True:
                # Wait for event with timeout to send keep-alive
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    event_type = event.get("type", "message")
                    yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
                    
                    if event_type == "complete" or event_type == "error":
                        break
                        
                except asyncio.TimeoutError:
                    # Keep-alive comment
                    yield ": keep-alive\n\n"
                    
        except asyncio.CancelledError:
            # Client disconnected
            pass
        finally:
            # Remove listener if possible (requires better clean up in FlowEventEmitter)
            if listener in emitter.listeners:
                emitter.listeners.remove(listener)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/status/{session_id}", response_model=SessionStatusResponse)
async def get_status(session_id: str):
    """
    Get current session status.
    
    Use this to poll for completion if not using SSE streaming.
    """
    state = get_session(session_id)
    
    # Log status poll for debugging skeleton visibility
    has_skeleton = state.skeleton is not None
    if has_skeleton:
        logger.debug(f"[STATUS_POLL] session={session_id[:8]}... status={state.status} skeleton=SET ({len(state.skeleton.slides)} slides)")
    else:
        logger.debug(f"[STATUS_POLL] session={session_id[:8]}... status={state.status} skeleton=NONE")
    
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

