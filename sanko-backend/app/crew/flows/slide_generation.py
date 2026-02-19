"""
Slide Generation Flow - Production Ready

Event-driven CrewAI Flow with:
- Database-backed pause points for user review
- Async slide generation for performance
- Real agent execution (not placeholders)
- SSE streaming of progress

Pause Points:
1. After Clarifier: OrderForm complete
2. After Outliner: User reviews/modifies skeleton
3. During Generation: Progress updates streamed

Architecture:
- Flow saves state to DB at pause points
- API endpoints resume the flow
- SSE streams progress to frontend
"""

from crewai.flow.flow import Flow, listen, router, start
from crewai import Crew, Task
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Callable
from uuid import UUID, uuid4
from datetime import datetime
from enum import Enum
import asyncio
import json
import os
import re
import hashlib

from app.models.schemas import (
    OrderForm,
    Skeleton,
    SkeletonSlide,
    SlideContentType,
    PlannedContent,
    PlannedSlide,
    RefinedContent,
    RefinedSlide,
    GeneratedPresentation,
    GeneratedSlide,
    QAResult,
    QAReport,
    CitationMetadata,
    GatheredInfo,
    ClarificationMessage,
    KnowledgeBase,
    ResearchFact,
    ResearchNeed,
    EvidenceRef,
)
from app.crew.agents.clarifier import create_clarifier_agent
from app.crew.agents.planner import create_planner_agent
from app.crew.agents.refiner import create_refiner_agent
from app.crew.agents.generator import create_generator_agent
from app.crew.agents.visual_qa import create_visual_qa_agent
from app.crew.agents.helper import (
    create_helper_agent,
    FailureContext,
    HelperDecision,
    RetryBudget,
    build_guardrail_prompt,
)
from app.crew.tools.render_service_tool import get_render_tool
from app.crew.tools.synthesis_tool import SynthesisTool, SynthesisError
from app.crew.tools.context_tool import (
    ReadSectionTool,
    ListSectionsTool,
    SearchSectionsTool,
    ReadSectionByIdTool,
)
from app.crew.tools.academic_search_tool import AcademicSearchTool
from app.crew.tools.doi_validator import DOIValidatorTool
from app.services.citation_utils import (
    extract_inline_citations,
    find_matching_citation,
    remove_inline_citation,
    extract_all_citations_from_slides,
    sort_citations,
)
from app.core.logging import get_logger
from app.core.config import settings
from app.services.cache import RedisCache
from app.crew.flows.metrics import (
    MetricsCollector,
    TokenUsage,
    extract_usage_from_response,
)

logger = get_logger(__name__)


# =============================================================================
# Flow Status Enum
# =============================================================================

class FlowStatus(str, Enum):
    """Pipeline status values."""
    SYNTHESIZING = "synthesizing"
    AWAITING_CLARIFICATION = "awaiting_clarification"
    CLARIFICATION_COMPLETE = "clarification_complete"
    AWAITING_OUTLINE_APPROVAL = "awaiting_outline_approval"
    OUTLINE_APPROVED = "outline_approved"
    GENERATING = "generating"
    QA_IN_PROGRESS = "qa_in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# =============================================================================
# Flow State (Database-backed)
# =============================================================================

class FlowState(BaseModel):
    """
    State passed between flow steps.
    
    This state is serialized to the database at pause points,
    allowing the flow to be resumed later.
    """
    
    # Session tracking
    session_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: Optional[str] = None
    project_id: Optional[str] = Field(default=None, description="Link to existing project")
    mode: Optional[str] = Field(default=None, description="Generation mode: deep_research, synthesis, or replica")
    topic: Optional[str] = Field(default=None, description="Initial topic for deep research mode")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Pipeline outputs (nullable for progressive population)
    order_form: Optional[OrderForm] = None
    skeleton: Optional[Skeleton] = None
    planned_content: Optional[PlannedContent] = None
    refined_content: Optional[RefinedContent] = None
    generated_presentation: Optional[GeneratedPresentation] = None
    qa_report: Optional[QAReport] = None
    
    # Synthesis Engine (NEW)
    knowledge_base: Optional[KnowledgeBase] = Field(
        default=None, 
        description="Structured content extracted from synthesis"
    )
    
    # R2 uploaded files tracking
    uploaded_files: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of uploaded file metadata (hash, r2_key, filename)"
    )
    
    # Clarification conversation tracking (NEW - fixes memory issue)
    conversation_history: List[ClarificationMessage] = Field(
        default_factory=list,
        description="Full conversation history for clarification phase"
    )
    gathered_info: Optional[GatheredInfo] = Field(
        default=None,
        description="Progressively tracked info from user during clarification"
    )
    
    # Document scope tracking (for zero-hallucination architecture)
    selected_sections: List[str] = Field(
        default_factory=list,
        description="Section titles user explicitly wants to focus on"
    )
    approved_related: List[str] = Field(
        default_factory=list,
        description="Related sections user approved for inclusion"
    )
    declined_related: List[str] = Field(
        default_factory=list,
        description="Related sections user declined (don't ask again)"
    )
    document_scoped: bool = Field(
        default=False,
        description="Whether user has specified which sections to use"
    )
    pending_related_sections: List[str] = Field(
        default_factory=list,
        description="Related sections we're asking user about"
    )
    
    # Current status
    status: FlowStatus = Field(default=FlowStatus.AWAITING_CLARIFICATION)
    current_stage: str = Field(default="clarifier")
    
    # QA tracking
    qa_loops: int = Field(default=0)
    max_qa_loops: int = Field(default=3)
    
    # Helper/retry tracking
    helper_attempts: Dict[str, int] = Field(default_factory=dict)
    failure_context: Optional[Dict[str, Any]] = None
    needs_helper: bool = Field(default=False, description="Whether QA escalated to Helper agent")
    helper_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Context for Helper agent (trigger, failed_slides, issues)"
    )
    
    # Error tracking
    error_message: Optional[str] = None
    
    # Progress tracking for async generation
    slides_completed: int = Field(default=0)
    total_slides: int = Field(default=0)
    
    class Config:
        arbitrary_types_allowed = True
        use_enum_values = True
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Convert to dict for database storage."""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "current_stage": self.current_stage,
            "order_form": self.order_form.model_dump() if self.order_form else None,
            "skeleton": self.skeleton.model_dump() if self.skeleton else None,
            "planned_content": self.planned_content.model_dump() if self.planned_content else None,
            "refined_content": self.refined_content.model_dump() if self.refined_content else None,
            "generated_slides": self.generated_presentation.model_dump() if self.generated_presentation else None,
            "knowledge_base": self.knowledge_base.model_dump() if self.knowledge_base else None,
            "qa_loops_count": self.qa_loops,
            "helper_retries": sum(self.helper_attempts.values()),
            "final_qa_score": self.qa_report.average_score if self.qa_report else None,
            "updated_at": datetime.utcnow(),
        }
    
    @classmethod
    def from_db(cls, db_session: Dict[str, Any]) -> "FlowState":
        """Restore state from database."""
        state = cls(
            session_id=str(db_session.get("id", uuid4())),
            status=FlowStatus(db_session.get("status", "awaiting_clarification")),
            current_stage=db_session.get("current_stage", "clarifier"),
            qa_loops=db_session.get("qa_loops_count", 0),
        )
        
        if db_session.get("order_form"):
            state.order_form = OrderForm(**db_session["order_form"])
        if db_session.get("skeleton"):
            state.skeleton = Skeleton(**db_session["skeleton"])
        if db_session.get("planned_content"):
            state.planned_content = PlannedContent(**db_session["planned_content"])
        if db_session.get("refined_content"):
            state.refined_content = RefinedContent(**db_session["refined_content"])
        if db_session.get("generated_slides"):
            state.generated_presentation = GeneratedPresentation(**db_session["generated_slides"])
        if db_session.get("knowledge_base"):
            state.knowledge_base = KnowledgeBase(**db_session["knowledge_base"])
        
        return state


# =============================================================================
# Event Emitter for SSE Streaming
# =============================================================================

class FlowEventEmitter:
    """
    Emits events for SSE streaming to frontend.
    
    Events:
    - stage_start: When a stage begins
    - stage_complete: When a stage completes
    - slide_progress: When a slide is generated (for async gen)
    - error: When an error occurs
    - pause: When awaiting user input
    - complete: When flow finishes
    """
    
    _instances: Dict[str, "FlowEventEmitter"] = {}
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.listeners: List[Callable] = []
        FlowEventEmitter._instances[session_id] = self
        
    @classmethod
    def get_or_create(cls, session_id: str) -> "FlowEventEmitter":
        if session_id in cls._instances:
            return cls._instances[session_id]
        return cls(session_id)
        
    @classmethod
    def get(cls, session_id: str) -> Optional["FlowEventEmitter"]:
        return cls._instances.get(session_id)
    
    def add_listener(self, callback: Callable):
        """Add an event listener."""
        self.listeners.append(callback)
    
    async def emit(self, event_type: str, data: Dict[str, Any]):
        """Emit an event to all listeners."""
        event = {
            "type": event_type,
            "session_id": self.session_id,
            "timestamp": datetime.utcnow().isoformat(),
            **data,
        }
        logger.info(f"[SSE] Emitting event: {event_type} | data={data}")
        for listener in self.listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    listener(event)
            except Exception as e:
                logger.error(f"Event listener error: {e}")
    
    async def stage_start(self, stage: str):
        await self.emit("stage_start", {"stage": stage})
    
    async def stage_complete(self, stage: str, result: Any = None):
        await self.emit("stage_complete", {"stage": stage, "result": result})
    
    async def slide_progress(self, slide_order: int, total: int, status: str = "completed"):
        await self.emit("slide_progress", {
            "slide_order": slide_order,
            "total": total,
            "status": status,
        })
    
    async def pause_for_review(self, review_type: str, data: Dict):
        await self.emit("pause", {"review_type": review_type, **data})
    
    async def progress(self, message: str, stage: str = None, details: Dict = None):
        """Emit a progress update event."""
        await self.emit("progress", {
            "message": message,
            "stage": stage,
            **(details or {}),
        })
    
    async def error(self, message: str, stage: str):
        await self.emit("error", {"message": message, "stage": stage})
    
    async def complete(self, presentation: GeneratedPresentation):
        await self.emit("complete", {"slides_count": presentation.total_slides})


# =============================================================================
# Slide Generation Flow - Production Ready
# =============================================================================

class SlideGenerationFlow:
    """
    Production-ready slide generation flow.
    
    Key features:
    - Async execution with pause points
    - Database-backed state persistence
    - SSE event streaming
    - Parallel slide generation for performance
    - Proper agent execution
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        event_emitter: Optional[FlowEventEmitter] = None,
    ):
        self.state = FlowState(session_id=session_id or str(uuid4()))
        self.emitter = event_emitter or FlowEventEmitter.get_or_create(self.state.session_id)
        self.retry_tracker = RetryBudget()
        self.metrics = MetricsCollector.get_or_create(self.state.session_id)
        # State is sometimes overwritten after construction (see flow runner helpers),
        # so context is also refreshed there. This initial set covers the common case.
        try:
            self.metrics.set_context(
                user_id=getattr(self.state, "user_id", None),
                project_id=getattr(self.state, "project_id", None),
                mode=getattr(self.state, "mode", None),
            )
        except Exception:
            pass
    
    # =========================================================================
    # Stage 0: Synthesis (Pre-processing)
    # =========================================================================

    async def run_synthesis(self, file_paths: List[str]) -> KnowledgeBase:
        """
        Run multimodal extraction on a list of PDF files (local paths).
        
        DEPRECATED: Use run_synthesis_from_r2 for R2-stored files.
        
        Args:
            file_paths: List of local paths to the uploaded PDFs.
            
        Returns:
            The combined KnowledgeBase.
        """
        await self.emitter.stage_start("synthesis")
        self.state.status = FlowStatus.SYNTHESIZING
        self.state.current_stage = "synthesis"
        
        synthesis_tool = SynthesisTool()
        
        # Combine results from all files
        all_sections = []
        combined_summary_parts = []
        
        for path in file_paths:
            logger.info(f"Synthesizing file: {path}")
            try:
                # Wrap the tool call in a thread pool since it's blocking
                loop = asyncio.get_running_loop()
                kb = await loop.run_in_executor(None, synthesis_tool._run, path)
                
                all_sections.extend(kb.sections)
                combined_summary_parts.append(f"Content from {os.path.basename(path)}: {kb.summary}")
            except SynthesisError as e:
                logger.error(f"Synthesis failed for {path}: {e}")
                await self.emitter.error(str(e), "synthesis")
                continue
            
        final_kb = KnowledgeBase(
            summary="\n\n".join(combined_summary_parts),
            sections=all_sections
        )
        
        self.state.knowledge_base = final_kb
        self.state.status = FlowStatus.AWAITING_CLARIFICATION
        
        await self.emitter.stage_complete("synthesis", {
            "sections_extracted": len(all_sections),
            "summary": final_kb.summary[:200] + "..."
        })
        
        return final_kb

    async def run_synthesis_from_r2(
        self,
        uploaded_files: List[Dict[str, Any]],
    ) -> KnowledgeBase:
        """
        Run multimodal extraction on files stored in R2 with PostgreSQL caching.
        
        This method:
        1. Checks PostgreSQL cache for each file (by hash)
        2. Uses cached KnowledgeBase if available (saves API cost)
        3. Downloads from R2 and runs synthesis only for uncached files
        4. Caches new results in PostgreSQL for future use
        5. Processes multiple files in parallel with asyncio.gather
        
        Args:
            uploaded_files: List of dicts with keys:
                - file_hash: SHA-256 hash of file content
                - r2_key: R2 storage key
                - filename: Original filename
                - size_bytes: File size
                - cached: Whether cache was found during upload
            
        Returns:
            The combined KnowledgeBase.
        """
        from app.services.storage import get_storage_service, PDFCacheService
        from app.core.database import get_async_session
        import time
        import tempfile
        
        logger.info(f"[SYNTHESIS] Starting synthesis for {len(uploaded_files)} file(s)")
        
        await self.emitter.stage_start("synthesis")
        self.state.status = FlowStatus.SYNTHESIZING
        self.state.current_stage = "synthesis"
        
        storage = get_storage_service()
        cache_service = PDFCacheService()
        synthesis_tool = SynthesisTool()
        
        # Collect results
        all_sections = []
        combined_summary_parts = []
        failed_files = []  # Track failed files for user feedback
        
        for idx, file_info in enumerate(uploaded_files, 1):
            file_hash = file_info["file_hash"]
            r2_key = file_info["r2_key"]
            filename = file_info.get("filename", "unknown.pdf")
            
            logger.info(f"[SYNTHESIS] [{idx}/{len(uploaded_files)}] Processing: {filename}")
            logger.info(f"[SYNTHESIS]   Hash: {file_hash[:16]}...")
            logger.info(f"[SYNTHESIS]   R2 Key: {r2_key}")
            
            # Step 1: Check cache (quick DB operation - separate session)
            logger.info("[SYNTHESIS]   Checking cache...")
            cached_kb = None
            try:
                async for db_session in get_async_session():
                    cached_kb = await cache_service.get_cached(file_hash=file_hash, db_session=db_session)
                    break
            except Exception as e:
                logger.warning(f"[SYNTHESIS]   Cache check failed: {e}")
            
            if cached_kb:
                logger.info("[SYNTHESIS]   ✓ CACHE HIT: Using pre-processed KnowledgeBase")
                logger.info(f"[SYNTHESIS]   → {len(cached_kb.sections)} sections, skipping Gemini API call")
                all_sections.extend(cached_kb.sections)
                combined_summary_parts.append(f"Content from {filename}: {cached_kb.summary}")
                continue
            
            # Avoid duplicate expensive extraction across concurrent workers.
            lock_key = f"pdfkb:lock:{file_hash}"
            lock_token = RedisCache.acquire_lock(lock_key, ttl=900)
            if not lock_token:
                logger.info("[SYNTHESIS]   Lock held by another worker, waiting for cache warm-up...")
                warmed = None
                for _ in range(12):  # ~60 seconds total
                    await asyncio.sleep(5)
                    try:
                        async for db_session in get_async_session():
                            warmed = await cache_service.get_cached(file_hash=file_hash, db_session=db_session)
                            break
                    except Exception:
                        warmed = None
                    if warmed:
                        logger.info("[SYNTHESIS]   Cache filled by peer worker")
                        all_sections.extend(warmed.sections)
                        combined_summary_parts.append(f"Content from {filename}: {warmed.summary}")
                        break

                if warmed:
                    continue

                logger.warning("[SYNTHESIS]   Lock wait timed out, proceeding in degraded mode")

            # Step 2: Download from R2 (no DB needed)
            logger.info("[SYNTHESIS]   ⏳ CACHE MISS: Gemini processing required")
            logger.info("[SYNTHESIS]   📥 Downloading from R2...")
            try:
                download_start = time.time()
                file_data = await storage.download_file(r2_key)
                download_time = (time.time() - download_start) * 1000
                logger.info(f"[SYNTHESIS]   ✓ Downloaded {len(file_data) / 1024:.1f}KB in {download_time:.0f}ms")
            except Exception as e:
                logger.error(f"[SYNTHESIS]   ✗ Failed to download from R2: {e}")
                await self.emitter.error(f"Download failed: {e}", "synthesis")
                failed_files.append({"filename": filename, "error": f"Download failed: {e}"})
                if lock_token:
                    RedisCache.release_lock(lock_key, lock_token)
                continue
            
            # Step 3: Run Gemini synthesis (long operation - NO DB connection held)
            tmp_path = None
            kb = None
            processing_time_ms = 0
            try:
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(file_data)
                    tmp_path = tmp.name
                
                logger.info("[SYNTHESIS]  Calling Gemini API for multimodal extraction...")
                logger.info("[SYNTHESIS]  This may take several minutes for large documents...")
                start_time = time.time()
                loop = asyncio.get_running_loop()
                kb = await loop.run_in_executor(None, synthesis_tool._run, tmp_path)
                processing_time_ms = int((time.time() - start_time) * 1000)
                
                logger.info(f"[SYNTHESIS]   ✓ Gemini processing complete in {processing_time_ms}ms")
                logger.info(f"[SYNTHESIS]   → Extracted {len(kb.sections)} sections")
                
            except SynthesisError as e:
                logger.error(f"[SYNTHESIS]   ✗ Gemini synthesis failed: {e}")
                await self.emitter.error(str(e), "synthesis")
                failed_files.append({
                    "filename": filename, 
                    "error": str(e),
                    "suggestion": "You can paste the relevant text content directly in the chat as a fallback."
                })
                continue
            except Exception as e:
                logger.error(f"[SYNTHESIS]   ✗ Unexpected error: {e}")
                await self.emitter.error(str(e), "synthesis")
                failed_files.append({"filename": filename, "error": f"Unexpected error: {e}"})
                if lock_token:
                    RedisCache.release_lock(lock_key, lock_token)
                continue
            finally:
                # Clean up temp file
                if tmp_path:
                    try:
                        os.unlink(tmp_path)
                    except:
                        pass
                if lock_token:
                    RedisCache.release_lock(lock_key, lock_token)
            
            # Step 4: Cache the result (fresh DB connection - quick operation)
            if kb:
                logger.info("[SYNTHESIS]  Saving to cache for future use...")
                try:
                    async for db_session in get_async_session():
                        await cache_service.save_cache(
                            file_hash=file_hash,
                            r2_key=r2_key,
                            knowledge_base=kb,
                            db_session=db_session,
                            original_filename=filename,
                            file_size_bytes=len(file_data),
                            processing_time_ms=processing_time_ms,
                        )
                        break
                    logger.info("[SYNTHESIS]   ✓ Cached successfully")
                except Exception as e:
                    logger.warning(f"[SYNTHESIS]   Cache save failed (non-fatal): {e}")
                    # Continue anyway - we have the KB in memory
                
                all_sections.extend(kb.sections)
                combined_summary_parts.append(f"Content from {filename}: {kb.summary}")

        # Store failed files info for user feedback
        if failed_files:
            self.state.failure_context = {"failed_synthesis": failed_files}
            logger.warning(f"[SYNTHESIS] {len(failed_files)} file(s) failed processing")
        
        final_kb = KnowledgeBase(
            summary="\n\n".join(combined_summary_parts) if combined_summary_parts else "",
            sections=all_sections
        )
        
        self.state.knowledge_base = final_kb
        self.state.status = FlowStatus.AWAITING_CLARIFICATION
        
        logger.info(f"[SYNTHESIS] Complete: {len(all_sections)} total sections from {len(uploaded_files)} file(s)")
        if failed_files:
            logger.info(f"[SYNTHESIS] {len(failed_files)} file(s) could not be processed")
        
        await self.emitter.stage_complete("synthesis", {
            "sections_extracted": len(all_sections),
            "files_processed": len(uploaded_files) - len(failed_files),
            "files_failed": len(failed_files),
            "summary": final_kb.summary[:200] + "..." if final_kb.summary else ""
        })
        
        return final_kb

    # =========================================================================
    # Stage 1: Clarification (Interactive)
    # =========================================================================
    
    async def process_clarification(self, user_message: str) -> Dict[str, Any]:
        """
        Process a clarification message from the user.
        
        This is called iteratively until OrderForm is complete.
        
        FIXED: Now properly tracks conversation history and passes it to agent.
        
        Args:
            user_message: User's response to clarification question
            
        Returns:
            - If more questions needed: {"complete": False, "question": "..."}
            - If done: {"complete": True, "order_form": OrderForm}
        """
        await self.emitter.stage_start("clarifier")
        
        # Initialize gathered_info if this is the first call
        if self.state.gathered_info is None:
            self.state.gathered_info = GatheredInfo()
        
        # Add user message to conversation history
        self.state.conversation_history.append(ClarificationMessage(
            role="user",
            content=user_message
        ))
        
        # Parse user message to update gathered info BEFORE asking agent
        self._extract_info_from_message(user_message)
        
        # Check if user has confirmed - if so, skip agent and complete automatically
        info = self.state.gathered_info
        
        # DEBUG: Log confirmation state
        logger.info(f"Confirmation state: confirmation_sent={info.confirmation_sent}, user_confirmed={info.user_confirmed}, is_fully_confirmed={info.is_fully_confirmed()}")
        
        if info.is_fully_confirmed():
            logger.info("User confirmed! Skipping agent and completing automatically...")
            # User confirmed! Create OrderForm from gathered info and complete
            order_form = OrderForm(
                presentation_title=info.title or "Untitled Presentation",
                target_audience=info.audience or "General audience",
                target_slides=info.slide_count or 10,
                focus_areas=info.focus_areas,
                key_topics=info.key_topics,
                tone=info.tone or "academic",
                emphasis_style=info.emphasis_style or "detailed",
                citation_style=info.citation_style or "apa",
                references_placement=info.references_placement or "last_slide",
                theme_id=info.theme or "modern",
                include_speaker_notes=False,  # Speaker notes not currently supported
                special_requests=info.special_requests or "",
                is_complete=True,
            )
            
            self.state.order_form = order_form
            self.state.status = FlowStatus.CLARIFICATION_COMPLETE
            
            # Add completion message to history
            self.state.conversation_history.append(ClarificationMessage(
                role="assistant",
                content="**Requirements confirmed!** I'm now ready to generate your presentation outline."
            ))
            
            await self.emitter.stage_complete("clarifier", {"order_form": order_form.model_dump()})
            
            return {
                "complete": True,
                "order_form": order_form.model_dump(),
                "message": "Requirements confirmed! Ready to generate your presentation.",
            }
        
        # Create clarifier agent with document tools if we have a knowledge base
        tools = []
        if self.state.knowledge_base:
            # Wire up tools for querying document sections
            # These enable the clarifier to read EXACT, VERBATIM content from PDFs
            tools.append(ListSectionsTool(kb=self.state.knowledge_base))
            tools.append(SearchSectionsTool(kb=self.state.knowledge_base))
            tools.append(ReadSectionTool(kb=self.state.knowledge_base))
            tools.append(ReadSectionByIdTool(kb=self.state.knowledge_base))
            logger.info(f"Wired {len(tools)} document tools to clarifier agent")
        
        clarifier = create_clarifier_agent(tools=tools)
        
        # Build the full context for the agent
        conversation_context = self._format_conversation_history()
        gathered_context = self._format_gathered_info()
        missing_required = info.get_missing_required()
        missing_optional = info.get_missing_optional()
        
        # Determine what stage we're in
        has_document = bool(self.state.knowledge_base and self.state.knowledge_base.sections)
        
        # =====================================================================
        # SCOPE-FIRST DOCUMENT HANDLING (Zero-Hallucination Architecture)
        # =====================================================================
        document_context = ""
        
        if has_document:
            # Phase 0: Try to detect scope from user's message
            if not self.state.document_scoped:
                detected_sections = self._detect_scope_from_message(user_message)
                
                if detected_sections:
                    # User already specified sections! Skip asking
                    logger.info(f"Scope detected from message: {detected_sections}")
                    self.state.selected_sections = detected_sections
                    self.state.document_scoped = True
                    self.state.gathered_info.document_acknowledged = True
                    
                    # Check for related sections to suggest
                    related = self._find_related_sections(detected_sections)
                    if related:
                        self.state.pending_related_sections = related
                        logger.info(f"Found related sections to suggest: {related}")
            
            # Phase 1.5: If we have pending related sections to ask about
            if self.state.pending_related_sections:
                related_list = ", ".join(self.state.pending_related_sections)
                selected_list = ", ".join(self.state.selected_sections)
                
                # Check if user responded to the related sections question
                msg_lower = user_message.lower()
                approve_patterns = ["include", "yes", "add", "both", "all", "sure"]
                decline_patterns = ["no", "just", "only", "skip", "don't"]
                
                if any(p in msg_lower for p in approve_patterns):
                    # User approved - add to approved_related
                    self.state.approved_related.extend(self.state.pending_related_sections)
                    self.state.pending_related_sections = []
                    logger.info("User approved related sections")
                elif any(p in msg_lower for p in decline_patterns):
                    # User declined - add to declined_related
                    self.state.declined_related.extend(self.state.pending_related_sections)
                    self.state.pending_related_sections = []
                    logger.info("User declined related sections")
                # else: still waiting for answer
            
            # Detect source preference from user message
            msg_lower = user_message.lower()
            pdf_only_patterns = ["only from", "just from", "exclusively from", "stick to the document", "just the pdf", "only the pdf", "just this document"]
            hybrid_patterns = ["also research", "supplement", "external sources", "you can research", "can also research", "add external"]
            
            if not info.has_source_preference:
                if any(p in msg_lower for p in pdf_only_patterns):
                    info.source_type = "pdf_only"
                    info.has_source_preference = True
                    logger.info("Detected source preference: pdf_only")
                elif any(p in msg_lower for p in hybrid_patterns):
                    info.source_type = "pdf_plus_research"
                    info.has_source_preference = True
                    logger.info("Detected source preference: pdf_plus_research")
            
            # Build the appropriate context
            if self.state.document_scoped:
                # Phase 2: Inject verbatim content of selected sections
                document_context = self._build_scoped_context()
            else:
                # Phase 1: Show structure only, ask for scope
                document_context = self._build_structure_only_context()
        else:
            # No document - research mode
            if not info.has_source_preference:
                info.source_type = "research_only"
                info.has_source_preference = True
            logger.info("No document uploaded - setting source_type: research_only")
        
        # =====================================================================
        # DETERMINE STAGE INSTRUCTION
        # =====================================================================
        
        if has_document and self.state.pending_related_sections:
            # Asking about related sections
            related_list = ", ".join(self.state.pending_related_sections)
            selected_list = ", ".join(self.state.selected_sections)
            
            stage_instruction = f"""## CURRENT STAGE: SUGGEST RELATED SECTIONS

You identified that the user wants to focus on: **{selected_list}**

I noticed these sections reference other sections that might provide helpful context:
**{related_list}**

ASK THE USER: "Would you like me to include context from these related sections as well, or should I focus only on the sections you mentioned?"

Wait for their answer before proceeding."""

        elif has_document and not self.state.document_scoped:
            # Need to ask user which sections to focus on
            stage_instruction = """## CURRENT STAGE: SCOPE DOCUMENT (CRITICAL)

The user has uploaded a document but hasn't specified which sections to focus on.

**YOUR RESPONSE MUST:**
1. Acknowledge you received the document
2. Show the document structure (sections found)
3. Ask: "Which sections would you like to focus on for your presentation?"

Do NOT proceed to other questions until user specifies scope.
This is critical for accuracy - we only work with content the user wants."""

        elif has_document and self.state.document_scoped and not self.state.gathered_info.document_acknowledged:
            # Scoped but not acknowledged yet
            selected_list = ", ".join(self.state.selected_sections)
            self.state.gathered_info.document_acknowledged = True
            
            stage_instruction = f"""## CURRENT STAGE: ACKNOWLEDGE SCOPE

User wants to focus on: **{selected_list}**

**YOUR RESPONSE MUST:**
1. Confirm you found these sections in the document
2. Briefly mention what content you have access to
3. Then proceed to gather other requirements (audience, slide count, etc.)

The document content is now available - you can reference specific facts from it."""

        elif has_document and self.state.document_scoped and info.document_acknowledged and not info.has_source_preference:
            # Document scoped and acknowledged, but need to ask about source preference
            stage_instruction = """## CURRENT STAGE: ASK SOURCE PREFERENCE

The user has selected their sections. Now ask about source preference:

**YOUR RESPONSE MUST:**
Ask: "Should I use content EXCLUSIVELY from this document, or can I supplement with external research if needed?"

This is important for academic accuracy - some users want citations only from their document, others want additional sources.

Wait for their answer before proceeding to gather other requirements."""

        elif info.needs_confirmation():
            stage_instruction = """## CURRENT STAGE: CONFIRMATION REQUIRED
All essential info is gathered. You MUST now:
1. Announce that you have gathered all necessary information.
2. State that a summary card has been generated for their review.
3. Explicitly ask them to review the card and click the confirmation button to proceed.

Example: "I have gathered all the necessary details for your presentation. A summary card has been generated above/below for your review. Please check the details and click the confirmation button to proceed."

DO NOT ask them to type "yes" or "confirm" - direct them to the UI button.
DO NOT output JSON yet - wait for the user to click the confirmation button!"""

        elif not missing_required:
            # Ready for confirmation
            stage_instruction = """## CURRENT STAGE: READY FOR CONFIRMATION
Required info is complete. Apply these intelligent defaults for any missing optional fields:
- Theme: Modern/Professional
- Citation: APA
- Tone: Academic
- Emphasis: Balanced

Then announce you are ready to finalize and ask them to use the confirmation card."""

        else:
            # Still gathering info
            stage_instruction = f"""## CURRENT STAGE: GATHER REQUIRED INFO
Still need: {', '.join(missing_required)}

Ask naturally about what's missing. You can ask about multiple things in one conversational question if it feels natural.

Be efficient - the user may have already told you some of this in their message!"""
        
        # Create task with FULL CONTEXT
        # IMPORTANT: When tools are attached, we must explicitly tell the agent
        # that asking questions is done via Final Answer, NOT via a tool
        tool_instruction = ""
        if tools:
            tool_instruction = """
## TOOL USAGE INSTRUCTIONS (CRITICAL)
You have access to document tools, but they are OPTIONAL:
- **List Document Sections**: Use ONLY if you need to see what content is available
- **Read Document Section**: Use ONLY if you need to verify or read specific content

**TO ASK QUESTIONS OR RESPOND TO THE USER**: Use `Final Answer` with your text response.
DO NOT try to use a tool called "Ask a clarifying question" - that tool does not exist!
Your question/response IS the Final Answer. Just write your question as plain text.

Example of correct behavior:
- Thought: I need to ask how many slides they want
- Final Answer: How many slides would you like in your presentation?

Example of INCORRECT behavior (DO NOT DO THIS):
- Action: Ask a clarifying question  <-- WRONG! This tool doesn't exist!
"""
        
        # Create task with the instruction
        task = Task(
            description=f"""{stage_instruction}

## CONVERSATION HISTORY
{conversation_context}

## INFORMATION ALREADY GATHERED
{gathered_context}

{document_context}

{tool_instruction}

## CRITICAL RULES
1. **ACCURACY FIRST** - Only reference facts that appear in the document content provided above
2. **NEVER re-confirm explicit statements** - If user said "harvard style", don't ask "Harvard style correct?"
3. **Scope before content** - If document is uploaded but not scoped, ask which sections to focus on
4. **Use intelligent defaults** - Don't ask about every optional field, apply sensible defaults
5. **DO NOT output JSON** until user explicitly confirms the summary
6. **TO RESPOND**: Use `Final Answer` with your text. Tools are optional for reading document details.

## RESPONSE FORMAT
- For document scoping: Show structure + ask "Which sections would you like to focus on?"
- For related sections: Ask if they want to include related sections
- For questions: Natural conversation (can ask about a couple things if it flows naturally)
- For confirmation: State you are done -> Ask user to use the confirmation card button
- For completion: Use `Final Answer` with OrderForm JSON

Be efficient and accurate - reference document content when relevant!""",
            expected_output="Either a document scoping question, a confirmation summary, clarifying questions, OR a complete OrderForm JSON",
            agent=clarifier,
        )
        
        try:
            # Execute via the shared retry/timeout wrapper (also records token + duration metrics).
            crew = Crew(agents=[clarifier], tasks=[task])
            from app.crew.utils.agent_execution import execute_crew_with_retry
            result = await execute_crew_with_retry(crew, "clarifier", session_id=self.state.session_id)
            
            # Parse the response
            response_text = str(result)
            
            # Add assistant response to history
            self.state.conversation_history.append(ClarificationMessage(
                role="assistant",
                content=response_text
            ))
            
            # Detect if this is a confirmation request from the agent
            import re
            confirmation_request_patterns = [
                r"does this look correct",
                r"is this correct",
                r"does this (look|seem) (right|good)",
                r"can you confirm",
                r"please confirm",
                r"ready to finalize",
                r"ready to proceed",
                r"proceed with these settings",
                r"click the confirmation button",
                r"use the confirmation button",
                r"review the card",
                r"check the details",
                r"summary card",
                r"finalize the presentation",
                r"if (this|everything) looks (good|correct)",
                r"let me (know|confirm)",
            ]
            response_lower = response_text.lower()
            if any(re.search(p, response_lower) for p in confirmation_request_patterns):
                self.state.gathered_info.confirmation_sent = True
                logger.info("Detected confirmation request in agent response. Set confirmation_sent=True")
            
            # Check if we got an OrderForm or a question
            if self._looks_like_order_form(response_text):
                order_form = self._parse_order_form(response_text)
                order_form.is_complete = True
                
                # Merge in any gathered info that wasn't in the JSON
                order_form = self._merge_gathered_info(order_form)
                
                self.state.order_form = order_form
                self.state.status = FlowStatus.CLARIFICATION_COMPLETE
                
                await self.emitter.stage_complete("clarifier", {"order_form": order_form.model_dump()})
                
                return {
                    "complete": True,
                    "order_form": order_form.model_dump(),
                    "message": "Requirements confirmed! Ready to generate your presentation.",
                }
            else:
                # It's a follow-up question
                if not self.state.order_form:
                    self.state.order_form = OrderForm()
                self.state.order_form.clarification_notes = response_text
                
                # Check if we should show confirmation UI:
                # 1. Agent explicitly asked for confirmation (regex detected)
                # 2. OR we heuristically determined we have enough info
                if self.state.gathered_info.confirmation_sent or self.state.gathered_info.is_ready_for_confirmation():
                    # Return needs_confirmation with structured summary for UI
                    # We usually keep the agent's question text so the user sees the summary/question
                    return {
                        "complete": False,
                        "needs_confirmation": True,
                        "question": response_text,  # Show the Agent's text/summary
                        "summary": self._build_summary_for_ui(),
                        "message": "Please review your presentation requirements:",
                    }
                else:
                    return {
                        "complete": False,
                        "question": response_text,
                    }
                
        except Exception as e:
            logger.error(f"Clarification failed: {e}")
            await self.emitter.error(str(e), "clarifier")
            raise
    
    def _format_conversation_history(self) -> str:
        """Format the full conversation history for the agent prompt."""
        if not self.state.conversation_history:
            return "(This is the start of the conversation)"
        
        formatted = []
        for msg in self.state.conversation_history:
            role_label = "USER" if msg.role == "user" else "ASSISTANT"
            formatted.append(f"{role_label}: {msg.content}")
        
        return "\n\n".join(formatted)
    
    def _format_gathered_info(self) -> str:
        """Format what we've gathered so far for the agent prompt."""
        info = self.state.gathered_info
        if not info:
            return "(Nothing gathered yet)"
        
        parts = []
        
        if info.title:
            parts.append(f"- **Title/Topic**: {info.title}")
        if info.let_agent_decide_title:
            parts.append("- **Title**: User wants you to decide")
            
        if info.audience:
            parts.append(f"- **Target Audience**: {info.audience}")
            
        if info.slide_count:
            parts.append(f"- **Number of Slides**: {info.slide_count}")
            
        if info.focus_areas:
            parts.append(f"- **Focus Areas**: {', '.join(info.focus_areas)}")
            
        if info.key_topics:
            parts.append(f"- **Key Topics**: {', '.join(info.key_topics)}")
            
        if info.emphasis_style:
            parts.append(f"- **Emphasis Style**: {info.emphasis_style}")
            
        if info.tone:
            parts.append(f"- **Tone**: {info.tone}")
            
        if info.citation_style:
            parts.append(f"- **Citation Style**: {info.citation_style}")
            
        if info.references_placement:
            parts.append(f"- **References Placement**: {info.references_placement}")
            
        if info.theme:
            parts.append(f"- **Theme**: {info.theme}")
        if info.let_agent_decide_theme:
            parts.append("- **Theme**: User wants you to decide")
            
        # Speaker notes not currently supported - removed from GatheredInfo
            
        if info.special_requests:
            parts.append(f"- **Special Requests**: {info.special_requests}")
        
        return "\n".join(parts) if parts else "(Nothing gathered yet)"
    
    def _build_summary_for_ui(self) -> Dict[str, Any]:
        """Build a structured summary dict for the frontend confirmation UI."""
        info = self.state.gathered_info
        
        return {
            "title": info.title or "(To be decided)",
            "audience": info.audience or "(Not specified)",
            "slide_count": info.slide_count or 10,
            "focus_areas": info.focus_areas if info.focus_areas else ["(To be decided)"],
            "emphasis_style": info.emphasis_style or "detailed",
            "tone": info.tone or "academic",
            "citation_style": info.citation_style or "apa",
            "references_placement": info.references_placement or "last_slide",
            "theme": info.theme if info.theme else ("(To be decided)" if not info.let_agent_decide_theme else "(Auto)"),
            "special_requests": info.special_requests or "",
            # Agent autonomy flags for UI display
            "agent_decides_title": info.let_agent_decide_title,
            "agent_decides_theme": info.let_agent_decide_theme,
            "agent_decides_citation": info.let_agent_decide_citation,
        }
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list of items for the prompt."""
        return "\n".join(f"- {item}" for item in items)
    
    # =========================================================================
    # Document Scope Detection (Zero-Hallucination Architecture)
    # =========================================================================
    
    def _detect_scope_from_message(self, user_message: str) -> List[str]:
        """
        Attempt to match user's message to specific sections.
        
        Returns list of section titles that match, or empty if no clear scope.
        This is used to skip asking "which sections?" when user already specified.
        """
        if not self.state.knowledge_base or not self.state.knowledge_base.sections:
            return []
        
        message_lower = user_message.lower()
        matched_sections = []
        
        for section in self.state.knowledge_base.sections:
            title_lower = section.title.lower()
            
            # Direct mention: "chapter 1", "section 2.1", exact title
            if title_lower in message_lower:
                if section.title not in matched_sections:
                    matched_sections.append(section.title)
                continue
            
            # Topic-based matching: "machine learning" matches "3. Machine Learning Approaches"
            # Extract keywords from section title (words > 3 chars, exclude numbers)
            import re
            keywords = [w for w in re.split(r'\W+', title_lower) if len(w) > 3 and not w.isdigit()]
            for kw in keywords:
                if kw in message_lower:
                    if section.title not in matched_sections:
                        matched_sections.append(section.title)
                    break
        
        return matched_sections
    
    def _find_related_sections(self, selected_titles: List[str]) -> List[str]:
        """
        Find sections that the selected sections reference.
        
        Looks for explicit references like "see Section 2.1" or mentions of other section titles.
        Returns section titles that are referenced but not already selected.
        """
        if not self.state.knowledge_base or not self.state.knowledge_base.sections:
            return []
        
        related = set()
        selected_set = set(selected_titles)
        
        # Get the content of selected sections
        for section in self.state.knowledge_base.sections:
            if section.title not in selected_set:
                continue
                
            content_lower = section.content.lower()
            
            # Look for references to other sections
            for other_section in self.state.knowledge_base.sections:
                if other_section.title in selected_set:
                    continue
                if other_section.title in related:
                    continue
                    
                other_title_lower = other_section.title.lower()
                
                # Check if this section is mentioned in the selected section's content
                if other_title_lower in content_lower:
                    related.add(other_section.title)
                    continue
                
                # Check for "section X" or "chapter X" references
                import re
                keywords = [w for w in re.split(r'\W+', other_title_lower) if len(w) > 3 and not w.isdigit()]
                for kw in keywords:
                    if f"see {kw}" in content_lower or f"in the {kw}" in content_lower:
                        related.add(other_section.title)
                        break
        
        # Exclude already approved or declined sections
        related -= set(self.state.approved_related)
        related -= set(self.state.declined_related)
        
        return list(related)
    
    def _build_structure_only_context(self) -> str:
        """
        Build context with only document structure (section titles + page ranges).
        
        Used when user hasn't specified which sections they want yet.
        Token-efficient because it doesn't include full content.
        """
        if not self.state.knowledge_base or not self.state.knowledge_base.sections:
            return ""
        
        context = f"""## UPLOADED DOCUMENT

**Document Summary:** {self.state.knowledge_base.summary}

### Document Structure:
"""
        
        for i, section in enumerate(self.state.knowledge_base.sections, 1):
            page_info = f" (Pages {section.page_range})" if section.page_range else ""
            visual_count = len(section.visuals) if section.visuals else 0
            visual_info = f" [{visual_count} visuals]" if visual_count > 0 else ""
            context += f"{i}. **{section.title}**{page_info}{visual_info}\n"
        
        context += "\n> 📋 Please specify which sections you want to focus on for your presentation."
        
        return context
    
    def _build_scoped_context(self) -> str:
        """
        Build context with FULL VERBATIM content of selected sections.
        
        Used after user has specified which sections they want.
        Includes all sections from selected_sections + approved_related.
        """
        if not self.state.knowledge_base or not self.state.knowledge_base.sections:
            return ""
        
        # Combine selected and approved related
        all_selected = set(self.state.selected_sections) | set(self.state.approved_related)
        
        if not all_selected:
            return self._build_structure_only_context()
        
        context_parts = ["## DOCUMENT CONTENT (Verbatim from selected sections)\n"]
        
        for section in self.state.knowledge_base.sections:
            if section.title not in all_selected:
                continue
                
            context_parts.append(f"""
### {section.title}
**Source: Pages {section.page_range or 'N/A'}**

{section.content}
""")
            
            # Include visual descriptions
            if section.visuals:
                context_parts.append("**Visual Elements:**")
                for visual in section.visuals:
                    context_parts.append(f"- {visual}")
                context_parts.append("")
            
            context_parts.append("---\n")
        
        context_parts.append("""
> ⚠️ **ACCURACY REQUIREMENT**: All content above is verbatim from the source document.
> Do NOT infer, guess, or add information that is not explicitly shown above.
> Any facts used must be directly from the sections provided.
""")
        
        return "\n".join(context_parts)
    
    def _extract_info_from_message(self, message: str) -> None:
        """
        Parse user message to extract and update gathered info.
        
        Uses heuristics to detect provided information.
        """
        import re
        info = self.state.gathered_info
        msg_lower = message.lower()
        
        # ---- Detect user confirmation ----
        confirmation_patterns = [
            r"^yes\b",
            r"^yeah\b",
            r"^yep\b",
            r"^correct\b",
            r"looks? (good|great|correct|right)",
            r"that('s| is) (correct|right|good)",
            r"^perfect\b",
            r"go ahead",
            r"finalize",
            r"sounds? (good|great|correct)",
            r"^lgtm\b",
        ]
        
        if info.confirmation_sent and any(re.search(p, msg_lower) for p in confirmation_patterns):
            info.user_confirmed = True
            logger.info("User confirmed! Set user_confirmed=True")
        
        # ---- Detect "decide yourself" patterns ----
        decide_patterns = [
            r"decide.*(yourself|for me|it yourself)",
            r"you (can |should )?(choose|pick|decide)",
            r"(pick|choose).*(yourself|for me)",
            r"up to you",
            r"your (choice|decision|call)",
        ]
        
        if any(re.search(p, msg_lower) for p in decide_patterns):
            if "title" in msg_lower or "topic" in msg_lower:
                info.let_agent_decide_title = True
                info.has_title = True  # Agent will handle
            if "theme" in msg_lower:
                info.let_agent_decide_theme = True
                info.has_theme = True  # Agent will handle
            if "citation" in msg_lower or "reference" in msg_lower:
                info.let_agent_decide_citation = True
                info.has_citation_style = True  # Agent will handle
        
        # ---- Detect audience ----
        audience_patterns = [
            (r"(university |college )?students", "university students"),
            (r"fellow students?", "fellow students"),
            (r"professors?|faculty|academics?", "academics/professors"),
            (r"executives?|management|c-suite", "executives"),
            (r"(business )?professionals?", "business professionals"),
            (r"engineers?|developers?|technical", "technical professionals"),
            (r"general (public|audience)", "general public"),
            (r"clients?|customers?", "clients"),
            (r"investors?|stakeholders?", "investors/stakeholders"),
        ]
        
        for pattern, audience_value in audience_patterns:
            if re.search(pattern, msg_lower):
                info.audience = audience_value
                info.has_audience = True
                break
        
        # Check for explicit audience statements
        audience_match = re.search(r"(target audience|presenting to|for)\s*(?:is\s*|:?\s*)([^,.]+)", msg_lower)
        if audience_match and not info.has_audience:
            info.audience = audience_match.group(2).strip()
            info.has_audience = True
        
        # ---- Detect slide count ----
        slide_patterns = [
            r"(\d+)\s*slides?",
            r"around\s*(\d+)",
            r"about\s*(\d+)\s*slides?",
            r"(\d+)\s*-\s*\d+\s*slides?",  # Range like "8-10 slides"
        ]
        
        for pattern in slide_patterns:
            match = re.search(pattern, msg_lower)
            if match:
                try:
                    count = int(match.group(1))
                    if 3 <= count <= 50:
                        info.slide_count = count
                        info.has_slide_count = True
                        break
                except ValueError:
                    pass
        
        # ---- Detect citation style ----
        citation_patterns = [
            (r"\bapa\b", "apa"),
            (r"\bieee\b", "ieee"),
            (r"\bharvard\b", "harvard"),
            (r"\bchicago\b", "chicago"),
            (r"\bmla\b", "apa"),  # Default to APA for MLA requests
        ]
        
        for pattern, style in citation_patterns:
            if re.search(pattern, msg_lower):
                info.citation_style = style
                info.has_citation_style = True
                break
        
        # ---- Detect references placement ----
        if any(phrase in msg_lower for phrase in ["last slide", "end", "at the end", "final slide"]):
            if "reference" in msg_lower or "citation" in msg_lower:
                info.references_placement = "last_slide"
                info.has_references_placement = True
        elif any(phrase in msg_lower for phrase in ["each slide", "distributed", "on relevant"]):
            if "reference" in msg_lower or "citation" in msg_lower:
                info.references_placement = "distributed"
                info.has_references_placement = True
        
        # ---- Detect emphasis style ----
        if any(word in msg_lower for word in ["detailed", "thorough", "in-depth", "comprehensive"]):
            info.emphasis_style = "detailed"
            info.has_emphasis_style = True
        elif any(word in msg_lower for word in ["concise", "brief", "short", "bullet", "minimal text"]):
            info.emphasis_style = "concise"
            info.has_emphasis_style = True
        elif any(word in msg_lower for word in ["visual", "images", "diagrams", "graphics"]):
            info.emphasis_style = "visual-heavy"
            info.has_emphasis_style = True
        
        # ---- Detect tone ----
        if any(word in msg_lower for word in ["academic", "scholarly", "formal", "research"]):
            info.tone = "academic"
            info.has_tone = True
        elif any(word in msg_lower for word in ["casual", "informal", "relaxed", "friendly"]):
            info.tone = "casual"
            info.has_tone = True
        elif any(word in msg_lower for word in ["technical", "engineering", "scientific"]):
            info.tone = "technical"
            info.has_tone = True
        elif any(word in msg_lower for word in ["persuasive", "convincing", "pitch", "sell"]):
            info.tone = "persuasive"
            info.has_tone = True
        
        # ---- Detect theme ----
        theme_patterns = [
            (r"\bdark\s*(mode|theme)?\b", "dark"),
            (r"\bminimal(ist)?\b", "minimal"),
            (r"\bmodern\b", "modern"),
            (r"\bacademic\b", "academic"),
            (r"\bprofessional\b", "modern"),
            (r"\bclean\b", "minimal"),
        ]
        
        for pattern, theme_value in theme_patterns:
            if re.search(pattern, msg_lower):
                info.theme = theme_value
                info.has_theme = True
                break
        
        # ---- Detect topic/title (if explicit) ----
        # Look for phrases like "about X" or "presentation on X"
        if not info.has_title and not info.let_agent_decide_title:
            topic_patterns = [
                r"(?:presentation |talk |slides? )?(?:about|on|regarding|covering)\s+[\"']?([^\"'\n.]+)[\"']?",
                r"topic\s*(?:is|:)\s*[\"']?([^\"'\n.]+)[\"']?",
                r"title\s*(?:is|should be|:)\s*[\"']?([^\"'\n.]+)[\"']?",
            ]
            
            for pattern in topic_patterns:
                match = re.search(pattern, msg_lower)
                if match:
                    topic = match.group(1).strip()
                    if len(topic) > 5:  # Avoid capturing short noise
                        info.title = topic
                        info.has_title = True
                        # Also treat as focus area
                        if topic not in info.focus_areas:
                            info.focus_areas.append(topic)
                            info.has_focus_areas = True
                        break
        
        # ---- Detect focus areas (key phrases) ----
        focus_patterns = [
            r"(?:focus on|emphasize|cover|include)\s+([^,.]+)",
            r"(?:specifically|mainly|primarily)\s+([^,.]+)",
        ]
        
        for pattern in focus_patterns:
            matches = re.findall(pattern, msg_lower)
            for match in matches:
                focus_item = match.strip()
                if len(focus_item) > 3 and focus_item not in info.focus_areas:
                    info.focus_areas.append(focus_item)
                    info.has_focus_areas = True
    
    def _merge_gathered_info(self, order_form: OrderForm) -> OrderForm:
        """Merge gathered info into order form, filling in any gaps."""
        info = self.state.gathered_info
        if not info:
            return order_form
        
        # Fill in any missing fields from gathered info
        if not order_form.presentation_title and info.title:
            order_form.presentation_title = info.title
        
        if order_form.target_audience == "General academic" and info.audience:
            order_form.target_audience = info.audience
        
        if order_form.target_slides == 10 and info.slide_count:
            order_form.target_slides = info.slide_count
        
        if not order_form.focus_areas and info.focus_areas:
            order_form.focus_areas = info.focus_areas
        
        if not order_form.key_topics and info.key_topics:
            order_form.key_topics = info.key_topics
        
        if info.emphasis_style:
            order_form.emphasis_style = info.emphasis_style
        
        if info.tone:
            order_form.tone = info.tone
        
        if info.citation_style:
            order_form.citation_style = info.citation_style
        
        if info.references_placement:
            order_form.references_placement = info.references_placement
        
        if info.theme:
            order_form.theme_id = info.theme
        
        if info.special_requests:
            order_form.special_requests = info.special_requests
        
        return order_form
    
    def _looks_like_order_form(self, text: str) -> bool:
        """Check if response looks like a complete OrderForm."""
        keywords = ["presentation_title", "target_audience", "theme_id", "citation_style"]
        return sum(1 for k in keywords if k in text.lower()) >= 2
    
    def _parse_order_form(self, text: str) -> OrderForm:
        """Parse OrderForm from agent response."""
        import re
        
        # Try to find JSON in the response
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return OrderForm(**data)
            except (json.JSONDecodeError, ValueError):
                pass
        
        # Fallback: create from gathered info
        info = self.state.gathered_info
        return OrderForm(
            presentation_title=info.title or "Untitled",
            target_audience=info.audience or "General academic",
            target_slides=info.slide_count or 10,
            focus_areas=info.focus_areas,
            key_topics=info.key_topics,
            is_complete=False,
        )
    
    # =========================================================================
    # Stage 2: Outliner (Pause for User Review)
    # =========================================================================
    
    async def generate_outline(self) -> Skeleton:
        """
        Generate the presentation skeleton for user review.
        
        This stage uses the Outliner agent to intelligently structure
        the presentation based on:
        - OrderForm (user preferences from Clarifier)
        - KnowledgeBase (document content from synthesis)
        
        The stage PAUSES after generating - user must call
        approve_outline() to continue.
        
        Returns:
            Generated Skeleton (also saved to state)
        """
        await self.emitter.stage_start("outliner")
        
        if not self.state.order_form or not self.state.order_form.is_complete:
            raise ValueError("Cannot generate outline: OrderForm not complete")
        
        order = self.state.order_form
        logger.info(f"[OUTLINER] Starting outline generation for {self.state.session_id[:8]}...")
        
        # Try CrewAI-based outline generation first
        try:
            skeleton = await self._run_outliner_agent()
            logger.info(f"[OUTLINER] Agent returned skeleton with {len(skeleton.slides)} slides")
        except Exception as e:
            logger.warning(f"[OUTLINER] Agent failed, using fallback: {e}")
            skeleton = self._generate_skeleton_fallback()
            logger.info(f"[OUTLINER] Fallback generated skeleton with {len(skeleton.slides)} slides")
        
            logger.info("[OUTLINER] Updating state.skeleton and status...")
        self.state.skeleton = skeleton
        self.state.status = FlowStatus.AWAITING_OUTLINE_APPROVAL
        self.state.total_slides = len(skeleton.slides)
        logger.info(f"[OUTLINER] ✅ State updated: status={self.state.status}, skeleton={len(self.state.skeleton.slides)} slides")
        
        await self.emitter.pause_for_review("outline", {
            "skeleton": skeleton.model_dump(),
        })
        
        return skeleton
    
    async def _run_outliner_agent(self) -> Skeleton:
        """
        Run the Outliner agent with CrewAI to generate an intelligent skeleton.
        
        This passes both the OrderForm and KnowledgeBase to the agent
        so it can make informed decisions about slide structure.
        """
        logger.info("Running Outliner agent with CrewAI")
        
        from app.crew.agents.outliner import create_outliner_agent, create_outliner_task
        
        # Create tools for document access if we have a knowledge base
        tools = []
        if self.state.knowledge_base:
            tools.append(ListSectionsTool(kb=self.state.knowledge_base))
            tools.append(SearchSectionsTool(kb=self.state.knowledge_base))
            tools.append(ReadSectionTool(kb=self.state.knowledge_base))
            tools.append(ReadSectionByIdTool(kb=self.state.knowledge_base))
        
        # Create agent with optional tools and iteration limit to prevent infinite loops
        outliner = create_outliner_agent(tools=tools if tools else None, max_iter=3)
        
        # Create task with OrderForm + KnowledgeBase
        task = create_outliner_task(
            agent=outliner,
            order_form=self.state.order_form,
            knowledge_base=self.state.knowledge_base,
        )
        
        # Execute with CrewAI using robust retry wrapper
        crew = Crew(agents=[outliner], tasks=[task])
        
        # Use retry wrapper with configurable timeout and automatic retries
        from app.crew.utils.agent_execution import execute_crew_with_retry
        result = await execute_crew_with_retry(crew, "outliner", session_id=self.state.session_id)
        
        # Parse the skeleton from agent output
        skeleton = self._parse_skeleton_from_result(result)
        
        logger.info(f"Outliner generated skeleton with {len(skeleton.slides)} slides")
        return skeleton
    
    def _parse_skeleton_from_result(self, result) -> Skeleton:
        """
        Parse Skeleton from CrewAI result.
        
        Handles both direct Pydantic output and JSON string parsing.
        """
        import re
        
        # If result has a pydantic attribute (output_pydantic worked)
        if hasattr(result, 'pydantic') and result.pydantic:
            return result.pydantic
        
        # Try to extract JSON from raw output
        raw_output = str(result)
        
        # Look for JSON block
        json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw_output)
        if json_match:
            raw_output = json_match.group(1).strip()
        
        # Try direct JSON parse
        try:
            data = json.loads(raw_output)
            return Skeleton(**data)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(f"Failed to parse skeleton JSON: {e}")
        
        # Last resort: find any JSON object
        json_match = re.search(r'\{[\s\S]*\}', raw_output)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return Skeleton(**data)
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse extracted JSON: {e}")
        
        # Fall back to fallback generator
        logger.warning("Could not parse outliner output, using fallback skeleton")
        return self._generate_skeleton_fallback()
    
    def _generate_skeleton_fallback(self) -> Skeleton:
        """
        Fallback skeleton generation when the Outliner agent fails.
        
        Creates a basic structure from OrderForm topics.
        """
        order = self.state.order_form
        slides = []
        slide_count = order.target_slides
        
        # Title slide
        slides.append(SkeletonSlide(
            order=1,
            title=order.presentation_title,
            content_type=SlideContentType.TITLE,
            description=f"Title slide for {order.presentation_title}",
        ))
        
        # Content slides based on key_topics and focus_areas
        topics = order.key_topics or ["Main Topic"]
        focus = order.focus_areas or []
        
        for i, topic in enumerate(topics[:slide_count - 2], start=2):
            is_focus = any(f.lower() in topic.lower() for f in focus)
            slides.append(SkeletonSlide(
                order=i,
                title=topic,
                content_type=SlideContentType.CONTENT,
                description=f"{'[FOCUS] ' if is_focus else ''}Content slide covering {topic}",
                needs_citation=True,
                citation_topic=topic,
            ))
        
        # Conclusion slide
        slides.append(SkeletonSlide(
            order=len(slides) + 1,
            title="Conclusion",
            content_type=SlideContentType.CONCLUSION,
            description="Summary and key takeaways",
        ))
        
        skeleton = Skeleton(
            presentation_title=order.presentation_title,
            target_audience=order.target_audience,
            narrative_arc=f"From introduction to {order.tone} conclusion",
            slides=slides,
            estimated_duration_minutes=len(slides) * 2,
        )
        
        return skeleton
    
    async def approve_outline(
        self,
        modifications: Optional[List[Dict]] = None,
        modified_skeleton: Optional[Dict] = None,
    ) -> Skeleton:
        """
        Approve the outline (with optional modifications).
        
        User can:
        - Add slides
        - Remove slides
        - Modify slide titles/descriptions
        - Reorder slides
        
        Args:
            modifications: List of changes to apply
            modified_skeleton: Full skeleton replacement (takes precedence)
            
        Returns:
            Updated Skeleton
        """
        if not self.state.skeleton:
            raise ValueError("No skeleton to approve")
        
        if modified_skeleton:
            # Full replacement from frontend
            try:
                # Ensure it's a valid Skeleton
                self.state.skeleton = Skeleton(**modified_skeleton)
            except Exception as e:
                logger.error(f"Failed to parse modified skeleton: {e}")
                raise ValueError(f"Invalid skeleton data: {e}")

        elif modifications:
            skeleton = self.state.skeleton
            
            for mod in modifications:
                action = mod.get("action")
                
                if action == "add":
                    # Add new slide
                    new_slide = SkeletonSlide(
                        order=mod.get("order", len(skeleton.slides) + 1),
                        title=mod.get("title", "New Slide"),
                        content_type=SlideContentType(mod.get("content_type", "content")),
                        description=mod.get("description", ""),
                    )
                    skeleton.slides.append(new_slide)
                    
                elif action == "remove":
                    # Remove slide by order
                    order_to_remove = mod.get("order")
                    skeleton.slides = [s for s in skeleton.slides if s.order != order_to_remove]
                    
                elif action == "modify":
                    # Modify existing slide
                    order_to_modify = mod.get("order")
                    for slide in skeleton.slides:
                        if slide.order == order_to_modify:
                            if "title" in mod:
                                slide.title = mod["title"]
                            if "description" in mod:
                                slide.description = mod["description"]
                            if "needs_diagram" in mod:
                                slide.needs_diagram = mod["needs_diagram"]
                            if "needs_equation" in mod:
                                slide.needs_equation = mod["needs_equation"]
                            break
                            
                elif action == "reorder":
                    # Reorder slides
                    new_order = mod.get("new_order", [])
                    if new_order:
                        ordered_slides = []
                        for i, order in enumerate(new_order, start=1):
                            for slide in skeleton.slides:
                                if slide.order == order:
                                    slide.order = i
                                    ordered_slides.append(slide)
                                    break
                        skeleton.slides = ordered_slides
            
            # Re-number slides
            for i, slide in enumerate(skeleton.slides, start=1):
                slide.order = i
            
            self.state.skeleton = skeleton
        
        self.state.status = FlowStatus.OUTLINE_APPROVED
        self.state.total_slides = len(self.state.skeleton.slides)
        
        await self.emitter.stage_complete("outliner", {
            "slides_count": len(self.state.skeleton.slides),
        })
        
        return self.state.skeleton
    
    # =========================================================================
    # Stage 3-6: Generation Pipeline (Async)
    # =========================================================================
    
    async def run_generation(self) -> GeneratedPresentation:
        """
        Run the full generation pipeline:
        Planner → Refiner → Citation Auditor → Final Slides → Generator → QA
        
        This runs asynchronously with progress streaming.
        For performance, individual slides can be generated in parallel.
        
        Returns:
            GeneratedPresentation with all slides
        """
        if self.state.status != FlowStatus.OUTLINE_APPROVED:
            raise ValueError(f"Cannot generate: status is {self.state.status}")
        
        self.state.status = FlowStatus.GENERATING
        self.metrics.start_pipeline()
        
        # Log pipeline start
        logger.info("[FLOW] ====== PIPELINE START ======")
        logger.info(f"[FLOW] Session: {self.state.session_id}")
        logger.info(f"[FLOW] Skeleton: {len(self.state.skeleton.slides)} slides")
        logger.info("[FLOW] Stages: Planner → Refiner → Citation Auditor → Final Slides → Generator → QA")
        
        # Emit pipeline_start for frontend
        await self.emitter.emit("pipeline_start", {
            "total_stages": 6,
            "stages": ["planner", "refiner", "citation_auditor", "final_slides", "generator", "visual_qa"],
        })
        
        try:
            # Stage 1: Planner
            logger.info("[FLOW] Starting Stage 1/6: Planner")
            await self._run_planner()
            logger.info("[FLOW] Completed Stage 1/6: Planner")
            
            # Stage 2: Refiner (with async asset rendering)
            logger.info("[FLOW] Starting Stage 2/6: Refiner")
            await self._run_refiner()
            logger.info("[FLOW] Completed Stage 2/6: Refiner")
            
            # Stage 3: Citation Auditor (verify all citations)
            logger.info("[FLOW] Starting Stage 3/6: Citation Auditor")
            await self._run_citation_auditor()
            logger.info("[FLOW] Completed Stage 3/6: Citation Auditor")

            # Strict zero-hallucination gate: fail fast if unsupported claims remain.
            if getattr(settings, "require_evidence_for_claims", False):
                unsupported = []
                for slide in (self.state.refined_content.slides if self.state.refined_content else []):
                    for claim in slide.unsupported_claims or []:
                        unsupported.append((slide.order, claim))
                if unsupported:
                    preview = "; ".join([f"slide {o}: {c[:80]}" for o, c in unsupported[:5]])
                    raise ValueError(
                        f"Unsupported factual claims remain after evidence audit ({len(unsupported)}). "
                        f"Examples: {preview}"
                    )
            
            # Stage 4: Generate References and Thank You slides
            logger.info("[FLOW] Starting Stage 4/6: Final Slides")
            await self._generate_final_slides()
            logger.info("[FLOW] Completed Stage 4/6: Final Slides")
            
            # Stage 5: Generator (parallel slide generation)
            logger.info("[FLOW] Starting Stage 5/6: Generator")
            await self._run_generator()
            logger.info("[FLOW] Completed Stage 5/6: Generator")
            
            # Stage 6: Visual QA
            logger.info("[FLOW] Starting Stage 6/6: Visual QA")
            await self._run_qa()
            logger.info("[FLOW] Completed Stage 6/6: Visual QA")
            
            self.state.status = FlowStatus.COMPLETED
            self.metrics.end_pipeline()
            
            logger.info("[FLOW] ====== PIPELINE COMPLETE ======")
            logger.info(f"[FLOW] Total slides: {self.state.generated_presentation.total_slides}")
            
            # Emit pipeline_complete for frontend
            await self.emitter.emit("pipeline_complete", {
                "success": True,
                "total_slides": self.state.generated_presentation.total_slides,
            })
            
            # Also emit the regular complete event
            await self.emitter.complete(self.state.generated_presentation)

            # PERSIST TO CONVEX
            try:
                from app.core.database import get_db
                client = get_db()
                if self.state.project_id:
                     # Convert Pydantic to dict for Convex
                    slides_data = self.state.generated_presentation.model_dump()
                    
                    # Run mutation in thread to avoid blocking loop
                    await asyncio.wait_for(
                        asyncio.to_thread(
                            client.mutation,
                            "projects:updateSlides", 
                            {
                                "projectId": self.state.project_id,
                                "slides": slides_data, 
                                "status": "completed"
                            }
                        ),
                        timeout=10.0
                    )
                    logger.info(f"[FLOW] Persisted results to Convex for project {self.state.project_id}")
            except Exception as e:
                logger.error(f"[FLOW] Failed to persist results to Convex: {e}")
            
            return self.state.generated_presentation
            
        except Exception as e:
            logger.error("[FLOW] ====== PIPELINE FAILED ======")
            logger.error(f"[FLOW] Error in stage '{self.state.current_stage}': {e}")
            import traceback
            logger.error(f"[FLOW] Traceback: {traceback.format_exc()}")
            
            self.state.status = FlowStatus.FAILED
            self.state.error_message = str(e)
            self.metrics.end_pipeline()
            
            # Emit pipeline_error for frontend
            await self.emitter.emit("pipeline_error", {
                "success": False,
                "stage": self.state.current_stage,
                "error": str(e),
            })
            
            await self.emitter.error(str(e), self.state.current_stage)

            # UPDATE CONVEX STATUS TO FAILED
            try:
                from app.core.database import get_db
                client = get_db()
                if self.state.project_id:
                    await asyncio.wait_for(
                        asyncio.to_thread(
                            client.mutation,
                            "projects:updateStatus", 
                            {
                                "projectId": self.state.project_id,
                                "status": "failed"
                            }
                        ),
                        timeout=10.0
                    )
            except Exception as ex:
                 logger.error(f"[FLOW] Failed to update failure status in Convex: {ex}")

            raise
    
    async def _run_planner(self):
        """Run the Planner agent to generate content."""
        await self.emitter.stage_start("planner")
        self.state.current_stage = "planner"
        
        # Import the comprehensive task creator
        from app.crew.agents.planner import create_planner_agent, create_planning_task
        
        logger.info("Running Planner agent with CrewAI")
        
        # Create agent (uses PRO model with high thinking)
        planner = create_planner_agent()
        
        # Create comprehensive task with full context
        task = create_planning_task(
            agent=planner,
            skeleton=self.state.skeleton,
            order_form=self.state.order_form,
            university_context=None,  # TODO: Pass university context when available
        )
        
        # Execute with CrewAI using robust retry wrapper
        crew = Crew(agents=[planner], tasks=[task])
        
        # Use retry wrapper with configurable timeout and automatic retries
        from app.crew.utils.agent_execution import execute_crew_with_retry
        result = await execute_crew_with_retry(crew, "planner", session_id=self.state.session_id)
        
        # Debug: Log what we got from CrewAI
        logger.info(f"[PLANNER] CrewAI result type: {type(result)}")
        logger.info(f"[PLANNER] CrewAI result dir: {[attr for attr in dir(result) if not attr.startswith('_')]}")
        
        # Try to get raw output - CrewAI result has different properties
        raw_output = None
        if hasattr(result, 'raw'):
            raw_output = result.raw
            logger.info(f"[PLANNER] Using result.raw ({len(raw_output)} chars)")
        elif hasattr(result, 'output'):
            raw_output = result.output
            logger.info(f"[PLANNER] Using result.output ({len(raw_output)} chars)")
        elif hasattr(result, 'result'):
            raw_output = result.result
            logger.info(f"[PLANNER] Using result.result ({len(raw_output)} chars)")
        else:
            raw_output = str(result)
            logger.info(f"[PLANNER] Using str(result) ({len(raw_output)} chars)")
        
        # Log first 500 chars to see what we're parsing
        logger.debug(f"[PLANNER] Raw output preview: {raw_output[:500] if raw_output else 'NONE'}")
        
        # Parse result into PlannedContent
        planned_content = self._parse_planned_content(raw_output)
        self.state.planned_content = planned_content
        
        logger.info(f"Planner generated content for {len(planned_content.slides)} slides")
        
        await self.emitter.stage_complete("planner", {
            "slides_planned": len(planned_content.slides),
        })
    
    def _build_planner_prompt(self) -> str:
        """Build the prompt for the Planner agent."""
        skeleton = self.state.skeleton
        order = self.state.order_form
        
        slides_list = "\n".join([
            f"- Slide {s.order}: {s.title} ({s.content_type.value})"
            f"\n  Description: {s.description}"
            f"\n  Needs diagram: {s.needs_diagram}, equation: {s.needs_equation}, citation: {s.needs_citation}, image: {s.needs_image}"
            f"\n  Image Description: {s.image_description if s.needs_image else 'None'}"
            for s in skeleton.slides
        ])
        
        return f"""Generate FULL content for this presentation.

## Presentation Info
Title: {skeleton.presentation_title}
Audience: {skeleton.target_audience}
Tone: {order.tone}
Emphasis Style: {order.emphasis_style}
Focus Areas: {', '.join(order.focus_areas) if order.focus_areas else 'None'}

## Slides to Write
{slides_list}

## Instructions
1. Write 3-5 substantial bullet points per slide (not placeholders!)
2. For slides needing citations, add `citation_queries` (search terms)
3. For slides needing diagrams, add `diagram_placeholder` (description)
4. For slides needing equations, add `equation_placeholder` (LaTeX description)
5. For slides needing images, add `image_query` (search term for finding/generating an image)
6. Add speaker_notes if requested: {order.include_speaker_notes}
7. Add `claims` (atomic factual claims) and `evidence_refs` for claim grounding when available.

Return a JSON object with 'slides' array containing PlannedSlide objects."""
    
    def _is_actual_slide_data(self, data: dict) -> bool:
        """
        Check if a JSON object contains actual slide data vs a schema definition.
        
        Schema definitions have:
        - "properties", "type": "object", "required", "items" as object
        
        Actual data has:
        - "slides" as a list with objects containing "order", "title", "content_type"
        """
        # Must have "slides" key
        if "slides" not in data:
            return False
        
        slides = data["slides"]
        
        # Slides must be a list for actual data (schema has it as an object)
        if not isinstance(slides, list):
            logger.debug(f"[PLANNER_PARSE] slides is not a list: {type(slides)}")
            return False
        
        # Must have at least one slide
        if len(slides) == 0:
            logger.debug("[PLANNER_PARSE] slides list is empty")
            return False
        
        # First slide must have "order" and "title" (actual slide data)
        first_slide = slides[0]
        if not isinstance(first_slide, dict):
            return False
        
        # Check for required fields in actual slide data
        if "order" in first_slide and "title" in first_slide:
            logger.debug(f"[PLANNER_PARSE] Found valid slide data with order={first_slide.get('order')}")
            return True
        
        # Check if it looks like a schema (has "properties" or "type": "object")
        if "properties" in data or data.get("type") == "object":
            logger.debug("[PLANNER_PARSE] Looks like a schema definition, skipping")
            return False
        
        return False
    
    def _parse_planned_content(self, text: str) -> PlannedContent:
        """Parse PlannedContent from agent response."""
        import re
        
        logger.info(f"[PLANNER_PARSE] Parsing PlannedContent from {len(text)} chars")
        logger.debug(f"[PLANNER_PARSE] First 200 chars: {text[:200]}")
        
        # Try multiple approaches to extract valid JSON
        json_data = None
        
        # Approach 1: Find JSON starting with {"presentation_title" or {"slides"
        # Look for actual data patterns (slides as array)
        json_patterns = [
            r'\{\s*"presentation_title"\s*:\s*"[^"]+[\s\S]*"slides"\s*:\s*\[',  # Real data pattern
            r'\{\s*"slides"\s*:\s*\[',  # Direct slides array
        ]
        
        for pattern in json_patterns:
            match = re.search(pattern, text)
            if match:
                logger.debug(f"[PLANNER_PARSE] Pattern matched at position {match.start()}")
                # Find the start of this JSON object
                start_pos = text.rfind('{', 0, match.end())
                if start_pos == -1:
                    start_pos = match.start()
                
                # Extract balanced JSON using brace counting
                json_str = self._extract_balanced_json(text[start_pos:])
                if json_str:
                    logger.debug(f"[PLANNER_PARSE] Extracted balanced JSON of {len(json_str)} chars")
                    try:
                        data = json.loads(json_str)
                        if self._is_actual_slide_data(data):
                            json_data = data
                            logger.info(f"[PLANNER_PARSE] ✅ Pattern match: valid slide data with {len(data['slides'])} slides")
                            break
                        else:
                            logger.debug("[PLANNER_PARSE] Pattern matched but not actual slide data")
                    except json.JSONDecodeError as e:
                        logger.warning(f"[PLANNER_PARSE] JSON decode failed: {e}")
                        continue
                else:
                    logger.warning("[PLANNER_PARSE] _extract_balanced_json returned None")
        
        # Approach 2: Try to find any valid JSON object with actual slide data
        if not json_data:
            logger.debug("[PLANNER_PARSE] Approach 1 failed, trying approach 2 (iterate all braces)")
            # Find all potential JSON starts
            for i, char in enumerate(text):
                if char == '{':
                    json_str = self._extract_balanced_json(text[i:])
                    if json_str:
                        try:
                            data = json.loads(json_str)
                            if self._is_actual_slide_data(data):
                                json_data = data
                                logger.info(f"[PLANNER_PARSE] ✅ Iteration found valid slide data with {len(data['slides'])} slides")
                                break
                        except json.JSONDecodeError:
                            continue
        
        if json_data and "slides" in json_data:
            try:
                return PlannedContent(
                    presentation_title=json_data.get("presentation_title", self.state.skeleton.presentation_title),
                    target_audience=json_data.get("target_audience", self.state.skeleton.target_audience),
                    theme_id=json_data.get("theme_id", self.state.order_form.theme_id),
                    citation_style=json_data.get("citation_style", self.state.order_form.citation_style),
                    slides=[PlannedSlide(**s) for s in json_data["slides"]],
                )
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to create PlannedContent from JSON: {e}")
        
        logger.warning("Using fallback PlannedContent from skeleton")
        # Fallback: generate from skeleton
        return PlannedContent(
            presentation_title=self.state.skeleton.presentation_title,
            target_audience=self.state.skeleton.target_audience,
            theme_id=self.state.order_form.theme_id,
            citation_style=self.state.order_form.citation_style,
            slides=[
                PlannedSlide(
                    order=s.order,
                    title=s.title,
                    content_type=s.content_type,
                    bullet_points=[s.description or "Content to be added"],
                )
                for s in self.state.skeleton.slides
            ],
        )
    
    def _extract_balanced_json(self, text: str) -> Optional[str]:
        """Extract a balanced JSON object from text using brace counting."""
        if not text or text[0] != '{':
            return None
        
        depth = 0
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            
            if char == '\\' and in_string:
                escape_next = True
                continue
            
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            
            if not in_string:
                if char == '{':
                    depth += 1
                elif char == '}':
                    depth -= 1
                    if depth == 0:
                        return text[:i + 1]
        
        return None

    def _extract_claims_from_bullets(self, bullet_points: List[str]) -> List[str]:
        """
        Extract atomic claims from slide bullet points.
        Conservative strategy: each non-empty bullet is treated as a claim candidate.
        """
        claims = []
        for bullet in bullet_points or []:
            cleaned = re.sub(r"\s+", " ", (bullet or "").strip())
            if cleaned:
                claims.append(cleaned)
        return claims

    def _lexical_overlap(self, a: str, b: str) -> int:
        a_tokens = set(re.findall(r"[A-Za-z0-9]{3,}", a.lower()))
        b_tokens = set(re.findall(r"[A-Za-z0-9]{3,}", b.lower()))
        if not a_tokens or not b_tokens:
            return 0
        return len(a_tokens.intersection(b_tokens))

    def _find_best_section_for_claim(self, claim: str):
        kb = self.state.knowledge_base
        if not kb or not kb.sections:
            return None

        best = None
        best_score = 0
        for section in kb.sections:
            score = self._lexical_overlap(claim, f"{section.title} {section.content[:3000]}")
            if score > best_score:
                best = section
                best_score = score
        return best if best_score >= 3 else None

    def _build_evidence_ref(self, claim: str, section) -> EvidenceRef:
        excerpt = (section.content or "").strip()
        excerpt = re.sub(r"\s+", " ", excerpt)
        if len(excerpt) > 240:
            excerpt = excerpt[:240] + "..."
        quote_hash = hashlib.sha256(excerpt.encode("utf-8", errors="ignore")).hexdigest()[:16]
        # Legacy KB sections may have empty section_id; generate a stable fallback.
        raw_section_id = getattr(section, "section_id", "") or ""
        if raw_section_id.strip():
            section_id = raw_section_id.strip()
        else:
            content = (getattr(section, "content", "") or "").encode("utf-8", errors="ignore")
            section_id = f"sec-{hashlib.sha256(content).hexdigest()[:24]}"
        evidence_id = f"ev-{section_id}-{quote_hash}"
        return EvidenceRef(
            evidence_id=evidence_id,
            section_id=section_id,
            page_range=section.page_range or "",
            quote_excerpt=excerpt,
            quote_hash=quote_hash,
            claim=claim,
            confidence=0.7,
            source_type="document",
        )

    def _enforce_slide_evidence(self, slide):
        """
        Attach evidence refs for claims and remove unsupported claims when strict mode is enabled.
        """
        strict = getattr(settings, "require_evidence_for_claims", False)
        claims = slide.claims or self._extract_claims_from_bullets(slide.bullet_points)
        slide.claims = claims

        existing_by_claim = {
            (e.claim or "").strip().lower(): e for e in (slide.evidence_refs or [])
        }
        verified_refs = []
        unsupported = []
        kept_bullets = []

        for claim in claims:
            key = claim.strip().lower()
            evidence = existing_by_claim.get(key)
            if not evidence:
                section = self._find_best_section_for_claim(claim)
                if section:
                    evidence = self._build_evidence_ref(claim, section)

            if evidence:
                verified_refs.append(evidence)
                kept_bullets.append(claim)
            else:
                unsupported.append(claim)
                if not strict:
                    kept_bullets.append(claim)

        slide.evidence_refs = verified_refs
        slide.unsupported_claims = unsupported

        if strict:
            slide.bullet_points = kept_bullets
            slide.all_claims_verified = len(unsupported) == 0
            slide.removed_claims = unsupported
        else:
            slide.all_claims_verified = len(unsupported) == 0
            if unsupported:
                slide.removed_claims = list({*slide.removed_claims, *unsupported})

        return slide
    
    async def _run_refiner(self):
        """
        Run the Refiner stage with hybrid approach:
        1. Agent converts placeholders to actual code (LaTeX/Mermaid)
        2. Programmatic rendering with RenderService (reliable)
        3. Agent-based citation search with AcademicSearchTool
        """
        await self.emitter.stage_start("refiner")
        self.state.current_stage = "refiner"
        
        logger.info("[REFINER] ====== Stage Start ======")
        logger.info(f"[REFINER] Planned slides: {len(self.state.planned_content.slides)}")
        
        render_tool = get_render_tool()
        academic_tool = AcademicSearchTool()
        citation_style = self.state.order_form.citation_style or "apa"
        
        # Import ImageSourceAgent for image search/verification
        from app.crew.agents.image_source_agent import ImageSourceAgent
        image_agent = ImageSourceAgent()
        
        try:
            # Step 1: Convert placeholders to code using agent
            logger.info("[REFINER] Step 1: Converting placeholders to code...")
            await self.emitter.progress("Converting placeholders to code...", stage="refiner")
            enhanced_content = await self._convert_placeholders_with_agent()
            logger.info(f"[REFINER] Step 1 complete: {len(enhanced_content.slides)} slides with converted placeholders")
            
            # Step 2: Process each slide - render assets and search citations
            logger.info("[REFINER] Step 2: Processing slides (render + citations)...")
            refined_slides = []
            total_slides = len(enhanced_content.slides)
            
            for i, planned_slide in enumerate(enhanced_content.slides):
                logger.info(f"[REFINER]   Processing slide {i+1}/{total_slides}: '{planned_slide.title}'")
                
                await self.emitter.slide_progress(
                    planned_slide.order, 
                    total_slides, 
                    "refining"
                )
                
                try:
                    # Refine the slide (render SVGs, search citations, source images)
                    refined_slide = await self._refine_slide_enhanced(
                        planned_slide, 
                        render_tool, 
                        academic_tool,
                        citation_style,
                        image_agent,
                    )
                    refined_slides.append(refined_slide)
                    
                    # Log what was rendered
                    eq_status = "✓" if refined_slide.equation_svg else "—"
                    diag_status = "✓" if refined_slide.diagram_svg else "—"
                    cit_count = len(refined_slide.citations) if refined_slide.citations else 0
                    img_status = "✓" if refined_slide.image_url else "—"
                    logger.info(f"[REFINER]   Slide {i+1} complete: eq={eq_status} diag={diag_status} cit={cit_count} img={img_status}")
                    
                except Exception as slide_error:
                    logger.error(f"[REFINER]   Slide {i+1} FAILED: {slide_error}")
                    # Create a minimal refined slide to continue
                    from app.models.schemas import RefinedSlide
                    refined_slides.append(RefinedSlide(
                        order=planned_slide.order,
                        title=planned_slide.title,
                        content_type=planned_slide.content_type,
                        bullet_points=planned_slide.bullet_points,
                        template_type=planned_slide.template_type,
                    ))
            
            # Build RefinedContent
            self.state.refined_content = RefinedContent(
                presentation_title=enhanced_content.presentation_title,
                target_audience=enhanced_content.target_audience,
                theme_id=enhanced_content.theme_id,
                citation_style=citation_style,
                slides=refined_slides,
                total_citations=sum(len(s.citations) for s in refined_slides if s.citations),
                equations_rendered=sum(1 for s in refined_slides if s.equation_svg),
                diagrams_rendered=sum(1 for s in refined_slides if s.diagram_svg),
            )
            
            # Post-process: Convert markdown in bullet points to HTML
            from app.services.markdown_processor import process_all_slides
            logger.info("[REFINER] Post-processing: Converting markdown to HTML...")
            self.state.refined_content.slides = process_all_slides(self.state.refined_content.slides)
            
            # Enforce claim-evidence ledger before generation.
            unsupported_total = 0
            for s in self.state.refined_content.slides:
                self._enforce_slide_evidence(s)
                unsupported_total += len(s.unsupported_claims or [])
            
            logger.info("[REFINER] ====== Stage Complete ======")
            logger.info(
                f"[REFINER] Results: {len(refined_slides)} slides, "
                f"{self.state.refined_content.equations_rendered} equations, "
                f"{self.state.refined_content.diagrams_rendered} diagrams, "
                f"{self.state.refined_content.total_citations} citations, "
                f"{unsupported_total} unsupported claims"
            )
            
            await self.emitter.stage_complete("refiner", {
                "slides_refined": len(refined_slides),
                "equations_rendered": self.state.refined_content.equations_rendered,
                "diagrams_rendered": self.state.refined_content.diagrams_rendered,
                "total_citations": self.state.refined_content.total_citations,
                "unsupported_claims": unsupported_total,
            })
            
        finally:
            await academic_tool.close()
            await image_agent.close()
    
    async def _run_citation_auditor(self) -> RefinedContent:
        """
        Run Citation Auditor to verify all citations.
        Position: After Refiner, before Generator
        
        This method:
        1. Extracts inline citations from each slide's bullet points
        2. Cross-references with slide.citations array
        3. Removes unverified inline citations from text
        4. Validates DOIs for citations that have them
        
        Returns:
            Updated RefinedContent with verified citations
        """
        await self.emitter.stage_start("citation_auditor")
        self.state.current_stage = "citation_auditor"
        
        logger.info("[CITATION AUDITOR] ====== Stage Start ======")
        import time
        auditor_start = time.time()
        
        refined = self.state.refined_content
        citation_style = self.state.order_form.citation_style or "apa"
        inline_format = "numbered" if citation_style == "ieee" else "author_year"
        
        removed_count = 0
        verified_count = 0
        
        # For each slide, verify inline citations
        for slide in refined.slides:
            for i, bullet in enumerate(slide.bullet_points):
                # Extract inline citations from this bullet point
                citations_found = extract_inline_citations(bullet, inline_format)
                
                # Process in reverse order to maintain string positions
                for author, year, start, end in reversed(citations_found):
                    # Check if citation exists in slide.citations
                    match = find_matching_citation(author, year, slide.citations)
                    
                    if not match:
                        # Citation not found - remove from text
                        slide.bullet_points[i] = remove_inline_citation(
                            slide.bullet_points[i], start, end
                        )
                        removed_count += 1
                        logger.warning(
                            f"[CITATION AUDITOR] Removed unverified citation: ({author}, {year})"
                        )
                    else:
                        verified_count += 1
        
        # Validate DOIs for all citations (optional enhancement)
        doi_tool = DOIValidatorTool()
        doi_validated = 0
        doi_invalid = 0
        
        for slide in refined.slides:
            for citation in slide.citations:
                if citation.doi and not citation.verified:
                    try:
                        result = await doi_tool._arun(citation.doi)
                        if result.get("valid"):
                            citation.verified = True
                            doi_validated += 1
                        else:
                            logger.warning(
                                f"[CITATION AUDITOR] Invalid DOI: {citation.doi} - {result.get('error')}"
                            )
                            doi_invalid += 1
                    except Exception as e:
                        logger.error(f"[CITATION AUDITOR] DOI validation error: {e}")

        logger.info("[CITATION AUDITOR] ====== Stage Complete ======")
        logger.info(
            f"[CITATION AUDITOR] Results: {verified_count} verified, "
            f"{removed_count} removed, {doi_validated} DOIs validated, {doi_invalid} invalid DOIs"
        )

        # Re-apply evidence enforcement after citation cleanup.
        unsupported_total = 0
        for slide in refined.slides:
            self._enforce_slide_evidence(slide)
            unsupported_total += len(slide.unsupported_claims or [])
        
        await self.emitter.stage_complete("citation_auditor", {
            "verified_citations": verified_count,
            "removed_citations": removed_count,
            "dois_validated": doi_validated,
            "dois_invalid": doi_invalid,
            "unsupported_claims": unsupported_total,
        })

        try:
            auditor_elapsed_ms = int((time.time() - auditor_start) * 1000)
            self.metrics.record("citation_auditor", TokenUsage(model="internal"), duration_ms=auditor_elapsed_ms)
        except Exception:
            pass
        
        return refined
    
    async def _generate_references_slide(self, include_images: bool = True) -> RefinedSlide:
        """
        Generate References slide with properly formatted citations.
        
        This method:
        1. Collects unique citations from all slides
        2. Sorts based on citation style (alphabetical for Harvard/APA, appearance for IEEE)
        3. Calls render service for HTML-formatted output
        4. Collects image citations (if include_images=True)
        5. Creates RefinedSlide with content_type=REFERENCES
        
        Returns:
            RefinedSlide for the References slide
        """
        import httpx
        from app.core.config import settings
        
        logger.info("[REFERENCES] Generating References slide...")
        
        refined = self.state.refined_content
        citation_style = self.state.order_form.citation_style or "apa"
        
        # Collect unique citations from all slides
        all_citations = extract_all_citations_from_slides(refined.slides)
        
        # Collect image citations if configured
        image_citations = []
        if include_images:
            figure_num = 0
            for slide in refined.slides:
                if slide.image_url:
                    figure_num += 1
                    if hasattr(slide, 'image_citation') and slide.image_citation:
                        # Don't include "Author's own work" or "AI-generated"
                        if slide.image_citation.source_type not in ["original", "generated"]:
                            image_citations.append({
                                "figure_number": figure_num,
                                "caption": slide.image_caption or slide.image_alt or "",
                                "citation": slide.image_citation.to_citation_string(),
                            })
        
        if not all_citations and not image_citations:
            logger.info("[REFERENCES] No citations or image sources found, skipping References slide")
            return None
        
        # Sort text citations based on style
        ordering = "appearance" if citation_style == "ieee" else "alphabetical"
        sorted_citations = sort_citations(all_citations, ordering) if all_citations else []
        
        # Format text citations using render service
        formatted_text_citations = []
        if sorted_citations:
            try:
                render_url = getattr(settings, 'RENDER_SERVICE_URL', 'http://localhost:3001')
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{render_url}/render/citation",
                        json={
                            "citations": [c.model_dump() for c in sorted_citations],
                            "style": citation_style,
                            "format": "html"
                        },
                        timeout=30.0
                    )
                    if response.status_code == 200:
                        result = response.json()
                        formatted_text_citations = [
                            c.get("formatted", "") for c in result.get("citations", [])
                        ]
                    else:
                        logger.warning(f"[REFERENCES] Render service returned {response.status_code}")
            except Exception as e:
                logger.error(f"[REFERENCES] Failed to format citations: {e}")
                # Fallback: use simple formatting
                for cit in sorted_citations:
                    authors = ", ".join(cit.authors) if cit.authors else "Unknown"
                    formatted_text_citations.append(f"{authors} ({cit.year}). {cit.title}.")
        
        # Format image citations (simple format)
        formatted_image_citations = [
            f"Figure {img['figure_number']}: {img['citation']}"
            for img in image_citations
        ]
        
        # Combine text and image citations
        all_formatted = formatted_text_citations.copy()
        if formatted_image_citations:
            all_formatted.append("")  # Blank line separator
            all_formatted.append("<strong>Figure Sources</strong>")
            all_formatted.extend(formatted_image_citations)
        
        # Create References slide
        next_order = len(refined.slides) + 1
        
        references_slide = RefinedSlide(
            order=next_order,
            title="References",
            content_type=SlideContentType.REFERENCES,
            bullet_points=[],  # References use formatted_citations instead
            citations=sorted_citations,
            formatted_citations=all_formatted,
            template_type="references",
        )
        
        logger.info(
            f"[REFERENCES] Created References slide with {len(formatted_text_citations)} citations "
            f"and {len(formatted_image_citations)} figure sources"
        )
        
        return references_slide
    
    async def _generate_final_slides(self):
        """
        Generate the References and Thank You slides.
        Position: After Citation Auditor, before Generator.
        """
        await self.emitter.stage_start("final_slides")
        self.state.current_stage = "final_slides"
        
        logger.info("[FINAL SLIDES] ====== Stage Start ======")
        import time
        final_start = time.time()
        
        slides_added = 0
        
        # Generate References slide (if there are citations)
        # Note: We pass include_images=True to include image citations
        references_slide = await self._generate_references_slide(include_images=True)
        if references_slide:
            self.state.refined_content.slides.append(references_slide)
            slides_added += 1
            logger.info("[FINAL SLIDES] Added References slide")
        
        # Generate Thank You slide
        thank_you_slide = self._generate_thank_you_slide()
        self.state.refined_content.slides.append(thank_you_slide)
        slides_added += 1
        logger.info("[FINAL SLIDES] Added Thank You slide")
        
        # Update total slides count
        self.state.total_slides = len(self.state.refined_content.slides)
        
        logger.info(f"[FINAL SLIDES] ====== Stage Complete: Added {slides_added} slides ======")
        
        await self.emitter.stage_complete("final_slides", {
            "slides_added": slides_added,
            "has_references": references_slide is not None,
        })
        try:
            final_elapsed_ms = int((time.time() - final_start) * 1000)
            self.metrics.record("final_slides", TokenUsage(model="internal"), duration_ms=final_elapsed_ms)
        except Exception:
            pass
    
    def _generate_thank_you_slide(self) -> RefinedSlide:
        """
        Generate a Thank You slide as the final slide.
        """
        from app.models.schemas import SlideContentType
        
        next_order = len(self.state.refined_content.slides) + 1
        
        return RefinedSlide(
            order=next_order,
            title="Thank You",
            content_type=SlideContentType.THANK_YOU,
            bullet_points=[
                "Questions?",
            ],
            template_type="thank_you",
            speaker_notes="Thank the audience for their attention and invite questions.",
        )
    
    async def _convert_placeholders_with_agent(self) -> PlannedContent:
        """
        Use Refiner agent to convert placeholder descriptions to actual code.
        
        Example:
            equation_placeholder="gradient descent update" 
            → equation_latex="\\theta = \\theta - \\alpha \\nabla J(\\theta)"
        """
        from app.crew.agents.refiner import create_refiner_agent
        
        # Check if there are any placeholders to convert
        has_placeholders = any(
            s.equation_placeholder or s.diagram_placeholder
            for s in self.state.planned_content.slides
        )
        
        if not has_placeholders:
            logger.info("No placeholders to convert, skipping agent call")
            return self.state.planned_content
        
        # Build a focused prompt just for code conversion
        slides_info = []
        for s in self.state.planned_content.slides:
            if s.equation_placeholder or s.diagram_placeholder:
                slides_info.append({
                    "order": s.order,
                    "title": s.title,
                    "equation_placeholder": s.equation_placeholder,
                    "diagram_placeholder": s.diagram_placeholder,
                })
        
        # Use a simplified task for code conversion
        conversion_prompt = f"""Convert the following placeholder descriptions to actual code.

For each slide:
1. If equation_placeholder exists, write valid LaTeX math code
2. If diagram_placeholder exists, write valid Mermaid diagram code

Slides requiring conversion:
{json.dumps(slides_info, indent=2)}

Return a JSON object with this structure:
{{
  "conversions": [
    {{
      "order": 1,
      "equation_latex": "LaTeX code here or null",
      "diagram_mermaid": "Mermaid code here or null"
    }}
  ]
}}

IMPORTANT:
- LaTeX should be valid math notation (e.g., "\\\\frac{{a}}{{b}}", "\\\\sum_{{i=1}}^{{n}}")
- Mermaid should be valid diagram syntax (graph TD, flowchart LR, sequenceDiagram, etc.)
- Only include slides that have placeholders
"""
        
        try:
            # Create agent and run conversion
            refiner = create_refiner_agent()
            task = Task(
                description=conversion_prompt,
                expected_output="JSON with LaTeX and Mermaid conversions",
                agent=refiner,
            )
            
            crew = Crew(agents=[refiner], tasks=[task])
            
            # Use retry wrapper with configurable timeout and automatic retries
            from app.crew.utils.agent_execution import execute_crew_with_retry
            result = await execute_crew_with_retry(crew, "refiner", session_id=self.state.session_id)
            
            # Parse conversions
            conversions = self._parse_conversions(str(result))
            
            # Apply conversions to planned content
            enhanced_slides = []
            for slide in self.state.planned_content.slides:
                # Find conversion for this slide
                conversion = conversions.get(slide.order, {})
                
                # Create enhanced slide with actual code
                enhanced_slide = PlannedSlide(
                    order=slide.order,
                    title=slide.title,
                    content_type=slide.content_type,
                    bullet_points=slide.bullet_points,
                    speaker_notes=slide.speaker_notes,
                    citation_queries=slide.citation_queries,
                    template_type=slide.template_type,
                    image_query=slide.image_query,
                    # Replace placeholders with actual code
                    equation_placeholder=conversion.get("equation_latex") or slide.equation_placeholder,
                    diagram_placeholder=conversion.get("diagram_mermaid") or slide.diagram_placeholder,
                )
                enhanced_slides.append(enhanced_slide)
            
            return PlannedContent(
                presentation_title=self.state.planned_content.presentation_title,
                target_audience=self.state.planned_content.target_audience,
                theme_id=self.state.planned_content.theme_id,
                citation_style=self.state.planned_content.citation_style,
                slides=enhanced_slides,
            )
            
        except Exception as e:
            logger.warning(f"Agent conversion failed, using fallback: {e}")
            return self.state.planned_content
    
    def _parse_conversions(self, text: str) -> dict:
        """Parse code conversions from agent output."""
        import re
        
        # Try to extract JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                conversions = data.get("conversions", [])
                return {c["order"]: c for c in conversions if "order" in c}
            except (json.JSONDecodeError, KeyError):
                pass
        
        return {}
    
    async def _refine_slide_enhanced(
        self, 
        planned: PlannedSlide, 
        render_tool,
        academic_tool: AcademicSearchTool,
        citation_style: str,
        image_agent: Optional["ImageSourceAgent"] = None,
    ) -> RefinedSlide:
        """
        Refine a single slide with full asset rendering, citation search, and image sourcing.
        
        Args:
            planned: The planned slide content
            render_tool: RenderServiceTool for SVG generation
            academic_tool: AcademicSearchTool for citation search
            citation_style: Citation format (apa, ieee, harvard, chicago, mla, vancouver)
            image_agent: Optional ImageSourceAgent for image search/verification
        """
        refined = RefinedSlide(
            order=planned.order,
            title=planned.title,
            content_type=planned.content_type,
            bullet_points=planned.bullet_points,
            template_type=planned.template_type or "content",
            speaker_notes=planned.speaker_notes,
            claims=planned.claims or self._extract_claims_from_bullets(planned.bullet_points),
            evidence_refs=planned.evidence_refs or [],
        )
        
        # Render equation if present
        if planned.equation_placeholder:
            try:
                # Check if it's already LaTeX code or still a description
                latex = planned.equation_placeholder
                if not any(cmd in latex for cmd in ['\\', '^', '_', '{', '}']):
                    # Still a description, use fallback
                    latex = self._placeholder_to_latex_fallback(latex)
                
                svg = render_tool._run(action="latex", content=latex)
                if not svg.startswith("Error"):
                    refined.equation_latex = latex
                    refined.equation_svg = svg
                    logger.debug(f"Rendered equation for slide {planned.order}")
                else:
                    logger.warning(f"Equation render failed: {svg}")
            except Exception as e:
                logger.warning(f"Failed to render equation for slide {planned.order}: {e}")
        
        # Render diagram if present
        if planned.diagram_placeholder:
            try:
                # Check if it's already Mermaid code or still a description
                mermaid = planned.diagram_placeholder
                # Expanded list of Mermaid diagram type keywords
                mermaid_keywords = [
                    'graph', 'flowchart', 'sequencediagram', 'classdiagram',
                    'pie', 'gantt', 'statediagram', 'erdiagram', 'journey',
                    'gitgraph', 'mindmap', 'timeline', 'quadrantchart',
                    'xychart', 'sankey', 'block',
                ]
                if not any(kw in mermaid.lower() for kw in mermaid_keywords):
                    # Still a description, use fallback
                    mermaid = self._placeholder_to_mermaid_fallback(mermaid)
                
                # Check for quadrantChart which has compatibility issues with Mermaid v10
                if mermaid.lower().startswith('quadrantchart'):
                    logger.warning("quadrantChart has compatibility issues, converting to graph")
                    mermaid = self._convert_quadrant_to_graph(mermaid)
                
                svg = render_tool._run(action="mermaid", content=mermaid)
                if not svg.startswith("Error"):
                    refined.diagram_mermaid = mermaid
                    refined.diagram_svg = svg
                    logger.debug(f"Rendered diagram for slide {planned.order}")
                else:
                    logger.warning(f"Diagram render failed: {svg}")
            except Exception as e:
                logger.warning(f"Failed to render diagram for slide {planned.order}: {e}")
        
        # Search and validate citations
        if planned.citation_queries:
            try:
                citations = []
                formatted_citations = []
                
                for query in planned.citation_queries[:3]:  # Limit to 3 queries per slide
                    results = await academic_tool.search(query, max_results=2)
                    
                    for citation in results:
                        citations.append(citation)
                        
                        # Format citation using RenderService
                        formatted = render_tool._run(
                            action="citation",
                            citation=citation.model_dump(),
                            style=citation_style,
                        )
                        if not formatted.startswith("Error"):
                            formatted_citations.append(formatted)
                
                refined.citations = citations
                refined.formatted_citations = formatted_citations
                
                if citations:
                    logger.debug(f"Found {len(citations)} citations for slide {planned.order}")
                    
            except Exception as e:
                logger.warning(f"Citation search failed for slide {planned.order}: {e}")
        
        # Search and source images using ImageSourceAgent
        if planned.image_query and image_agent:
            try:
                logger.info(f"[REFINER] Sourcing image for slide {planned.order}: '{planned.image_query}'")
                
                image_result = await image_agent.find_image(
                    query=planned.image_query,
                    slide_context=planned.title,
                )
                
                refined.image_url = image_result.image_url
                refined.image_alt = image_result.image_alt
                refined.image_caption = image_result.image_caption
                refined.image_citation = image_result.citation
                
                logger.info(
                    f"[REFINER] Image sourced for slide {planned.order}: "
                    f"method={image_result.source_method}, score={image_result.verification_score:.2f}"
                )
                
            except Exception as e:
                logger.warning(f"Image sourcing failed for slide {planned.order}: {e}")
        
        # Process research needs - extract facts from papers and integrate into content
        if hasattr(planned, 'research_needs') and planned.research_needs:
            try:
                research_facts = []
                papers_used = []
                
                for need in planned.research_needs:
                    # Skip common knowledge - no research needed
                    if need.is_common_knowledge:
                        logger.debug(f"[RESEARCH] Skipping common knowledge: {need.claim[:50]}...")
                        continue
                    
                    if not need.query:
                        continue
                    
                    # Search for papers supporting this claim
                    logger.info(f"[RESEARCH] Searching for: {need.query}")
                    papers = await academic_tool.search(need.query, max_results=3)
                    
                    if not papers:
                        logger.debug(f"[RESEARCH] No papers found for: {need.query}")
                        continue
                    
                    # Extract facts from paper abstracts
                    for paper in papers:
                        if not paper.abstract:
                            continue
                        
                        # Create a research fact from the abstract
                        # In a future enhancement, this could use LLM to extract specific facts
                        fact = ResearchFact(
                            fact=paper.abstract[:300],  # Use abstract as the fact
                            source=paper,
                            confidence=paper.relevance_score,
                            extraction_source="abstract",
                        )
                        research_facts.append(fact)
                        
                        # Track which papers we actually used
                        if paper not in papers_used:
                            papers_used.append(paper)
                        
                        # Limit to one paper per research need
                        break
                
                # Store research facts
                refined.research_facts = research_facts
                
                # Only cite papers whose content we actually used
                if papers_used:
                    for paper in papers_used:
                        if paper not in refined.citations:
                            refined.citations.append(paper)
                            
                            # Format citation
                            formatted = render_tool._run(
                                action="citation",
                                citation=paper.model_dump(),
                                style=citation_style,
                            )
                            if not formatted.startswith("Error"):
                                refined.formatted_citations.append(formatted)
                    
                    logger.info(
                        f"[RESEARCH] Slide {planned.order}: Extracted {len(research_facts)} facts, "
                        f"citing {len(papers_used)} papers"
                    )
                
            except Exception as e:
                logger.warning(f"Research processing failed for slide {planned.order}: {e}")
        
        return self._enforce_slide_evidence(refined)
    
    def _placeholder_to_latex_fallback(self, placeholder: str) -> str:
        """
        Fallback: Convert placeholder description to LaTeX when agent fails.
        Maps common mathematical concepts to their formulas.
        """
        placeholder_lower = placeholder.lower()
        
        # Common mathematical formulas
        latex_map = {
            "linear regression": r"y = \beta_0 + \beta_1 x + \epsilon",
            "quadratic formula": r"x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}",
            "quadratic equation": r"ax^2 + bx + c = 0",
            "gradient descent": r"\theta = \theta - \alpha \nabla J(\theta)",
            "mean squared error": r"MSE = \frac{1}{n} \sum_{i=1}^{n} (y_i - \hat{y}_i)^2",
            "softmax": r"\sigma(z)_j = \frac{e^{z_j}}{\sum_{k=1}^{K} e^{z_k}}",
            "sigmoid": r"\sigma(x) = \frac{1}{1 + e^{-x}}",
            "normal distribution": r"f(x) = \frac{1}{\sigma\sqrt{2\pi}} e^{-\frac{(x-\mu)^2}{2\sigma^2}}",
            "bayes theorem": r"P(A|B) = \frac{P(B|A) \cdot P(A)}{P(B)}",
            "euler": r"e^{i\pi} + 1 = 0",
            "pythagorean": r"a^2 + b^2 = c^2",
            "derivative": r"\frac{df}{dx} = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}",
            "integral": r"\int_a^b f(x) \, dx",
            "summation": r"\sum_{i=1}^{n} x_i",
            "cross entropy": r"H(p, q) = -\sum_{x} p(x) \log q(x)",
            "chain rule": r"\frac{dy}{dx} = \frac{dy}{du} \cdot \frac{du}{dx}",
        }
        
        for key, latex in latex_map.items():
            if key in placeholder_lower:
                return latex
        
        # Generic fallback
        return r"f(x) = \sum_{i=1}^{n} x_i"
    
    def _placeholder_to_mermaid_fallback(self, placeholder: str) -> str:
        """
        Fallback: Convert placeholder description to Mermaid when agent fails.
        Creates a simple flowchart based on the description.
        """
        placeholder_lower = placeholder.lower()
        
        # Try to detect diagram type from description
        if any(kw in placeholder_lower for kw in ['sequence', 'interaction', 'message']):
            return f"""sequenceDiagram
    participant A as Client
    participant B as Server
    A->>B: Request
    B-->>A: Response"""
        
        elif any(kw in placeholder_lower for kw in ['class', 'inheritance', 'object']):
            return f"""classDiagram
    class {placeholder.split()[0].title()}
    {placeholder.split()[0].title()} : +method()
    {placeholder.split()[0].title()} : -attribute"""
        
        elif any(kw in placeholder_lower for kw in ['pie', 'distribution', 'percentage']):
            return """pie title Distribution
    "Category A" : 40
    "Category B" : 35
    "Category C" : 25"""
        
        elif any(kw in placeholder_lower for kw in ['matrix', '2x2', 'quadrant', 'four']):
            # Quadrant/matrix diagram as a graph (quadrantChart has v10 compatibility issues)
            return """graph TD
    subgraph High["High"]
        A["Quadrant 1"]
        B["Quadrant 2"]
    end
    subgraph Low["Low"]
        C["Quadrant 3"]
        D["Quadrant 4"]
    end
    A --- B
    C --- D
    A --- C
    B --- D"""
        
        else:
            # Default flowchart
            return f"""graph TD
    A[Start] --> B[{placeholder}]
    B --> C[Process]
    C --> D[End]"""
    
    def _convert_quadrant_to_graph(self, quadrant_code: str) -> str:
        """
        Convert quadrantChart code to a compatible graph diagram.
        
        quadrantChart has compatibility issues with Mermaid v10 CDN,
        so we convert it to a simple subgraph-based representation.
        """
        # Extract title if present
        title = "Quadrant Analysis"
        lines = quadrant_code.strip().split('\n')
        for line in lines:
            if 'title' in line.lower():
                title = line.split('title', 1)[-1].strip()
                break
        
        # Return a compatible graph diagram
        return f"""graph TD
    subgraph "{title}"
        direction TB
        subgraph High["High Risk"]
            Q1["Routine Manual"]
            Q2["Routine Cognitive"]
        end
        subgraph Low["Lower Risk"]
            Q3["Non-Routine Manual"]
            Q4["Non-Routine Cognitive"]
        end
    end
    Q1 --- Q2
    Q3 --- Q4
    Q1 --- Q3
    Q2 --- Q4"""
    async def _run_generator(self):
        """
        Run the Generator - parallel slide HTML generation using templates.
        
        Uses DATABASE templates when available, with fallback to hardcoded templates.
        Features:
        - Proper slide layouts (title, content, diagram, etc.)
        - University branding (badge, name)
        - Slide numbering ("1 of 10")
        - Theme-specific layout styles
        """
        await self.emitter.stage_start("generator")
        self.state.current_stage = "generator"
        
        # Get theme and branding configuration
        from app.themes import get_theme, UniversityBranding
        
        theme = get_theme(self.state.order_form.theme_id or "modern")
        
        # Get layout style from theme (for DB template variant selection)
        layout_style = getattr(theme, 'layout_style', 'default') or 'default'
        
        # Create branding from university context if available
        branding = UniversityBranding()
        if hasattr(self.state, 'university_context') and self.state.university_context:
            branding = UniversityBranding(
                university_name=self.state.university_context.university_name or "",
                university_badge_url=self.state.university_context.badge_url or None,
            )
        
        total_slides = len(self.state.refined_content.slides)
        
        # Assign layouts to slides using the variety engine
        from app.services.layout_selector import get_layout_selector
        layout_selector = get_layout_selector()
        
        # Get user preferences from order_form if available
        user_layout_preferences = getattr(self.state.order_form, 'template_preferences', {}) or {}
        
        # Select layouts for all slides with variety
        slide_layouts = await layout_selector.select_for_presentation(
            slides=self.state.refined_content.slides,
            user_preferences=user_layout_preferences,
        )
        
        # Apply selected layouts to slides
        for slide in self.state.refined_content.slides:
            if slide.order in slide_layouts:
                layout = slide_layouts[slide.order]
                if not slide.layout_preset_id:
                    slide.layout_preset_id = layout.get("preset_id")
                logger.debug(f"Slide {slide.order}: assigned layout '{layout.get('preset_id')}'")

        # Optionally materialize structured element trees before html generation.
        if settings.enable_element_tree_pipeline:
            from app.core.layout_engine import layout_slide
            from app.core.layout_presets import has_layout_preset

            for slide in self.state.refined_content.slides:
                preferred_preset = slide.layout_preset_id if slide.layout_preset_id else None
                if preferred_preset and not has_layout_preset(preferred_preset):
                    logger.debug(
                        "Slide %s layout preset '%s' not found in element-tree registry; falling back to content-based preset",
                        slide.order,
                        preferred_preset,
                    )
                    preferred_preset = None

                slide.element_tree = layout_slide(slide=slide, preset_id=preferred_preset)
        
        
        # Generate slides in parallel
        import time
        generator_start = time.time()

        async def generate_slide(slide, slide_number):
            return await self._generate_slide_html_with_db_template(
                slide, 
                theme, 
                branding, 
                slide_number=slide_number,
                total_slides=total_slides,
                layout_style=layout_style,
            )
        
        tasks = [
            generate_slide(slide, i+1)
            for i, slide in enumerate(self.state.refined_content.slides)
        ]
        
        generated_slides = await asyncio.gather(*tasks)
        generator_elapsed_ms = int((time.time() - generator_start) * 1000)
        try:
            # Record stage duration (no tokens; this is template rendering, not LLM usage).
            self.metrics.record("generator", TokenUsage(model="template"), duration_ms=generator_elapsed_ms)
        except Exception:
            pass
        
        self.state.generated_presentation = GeneratedPresentation(
            title=self.state.refined_content.presentation_title,
            theme_id=self.state.refined_content.theme_id,
            slides=generated_slides,
            total_slides=len(generated_slides),
        )
        
        logger.info(f"Generator complete: {len(generated_slides)} slides with theme '{theme.id}' (layout: {layout_style})")
        
        await self.emitter.stage_complete("generator", {
            "slides_generated": len(generated_slides),
            "theme_id": theme.id,
            "layout_style": layout_style,
        })

    async def _generate_slide_html_with_db_template(
        self, 
        refined: RefinedSlide,
        theme,
        branding,
        slide_number: int,
        total_slides: int,
        layout_style: str = "default",
    ) -> GeneratedSlide:
        """
        Generate HTML for a single slide using DATABASE templates with fallback.
        
        This is the preferred method for production slide generation.
        It queries the database for Jinja2 templates and falls back to
        hardcoded Python templates if not found.
        """
        from app.templates.html_generator import generate_slide_html_with_db_template, element_tree_to_html
        from app.routers.generation.models import EnrichedSlide
        
        await self.emitter.slide_progress(refined.order, total_slides, "generating")
        
        # Convert RefinedSlide to EnrichedSlide for template compatibility
        enriched = EnrichedSlide(
            order=refined.order,
            title=refined.title,
            content_type=refined.content_type.value if hasattr(refined.content_type, 'value') else refined.content_type,
            bullet_points=refined.bullet_points,
            equation_latex=refined.equation_latex,
            equation_svg=refined.equation_svg,
            diagram_mermaid=refined.diagram_mermaid,
            diagram_svg=refined.diagram_svg,
            image_url=refined.image_url,
            image_alt=refined.image_alt,
            speaker_notes=refined.speaker_notes,
            formatted_citations=refined.formatted_citations or [],
        )
        
        # Prefer structured rendering path when the element tree exists.
        if refined.element_tree is not None:
            html = element_tree_to_html(tree=refined.element_tree, theme=theme)
        else:
            # Generate HTML using DATABASE-AWARE template system
            html = await generate_slide_html_with_db_template(
                slide=enriched,
                theme=theme,
                colors=theme.colors,
                branding=branding,
                slide_number=slide_number,
                total_slides=total_slides,
                layout_style=layout_style,
            )
        
        self.state.slides_completed += 1
        
        return GeneratedSlide(
            order=refined.order,
            title=refined.title,
            theme_id=theme.id,
            rendered_html=html,
            element_tree=refined.element_tree,
            speaker_notes=refined.speaker_notes,
        )
    
    async def _generate_slide_html_with_template(

        self, 
        refined: RefinedSlide,
        theme,
        branding,
        slide_number: int,
        total_slides: int,
    ) -> GeneratedSlide:
        """Generate HTML for a single slide using the template system."""
        from app.templates.html_generator import generate_slide_html_with_branding, element_tree_to_html
        from app.routers.generation.models import EnrichedSlide
        
        await self.emitter.slide_progress(refined.order, total_slides, "generating")
        
        # Convert RefinedSlide to EnrichedSlide for template compatibility
        enriched = EnrichedSlide(
            order=refined.order,
            title=refined.title,
            content_type=refined.content_type.value if hasattr(refined.content_type, 'value') else refined.content_type,
            bullet_points=refined.bullet_points,
            equation_latex=refined.equation_latex,
            equation_svg=refined.equation_svg,
            diagram_mermaid=refined.diagram_mermaid,
            diagram_svg=refined.diagram_svg,
            image_url=refined.image_url,
            image_alt=refined.image_alt,
            speaker_notes=refined.speaker_notes,
            formatted_citations=refined.formatted_citations or [],
        )
        
        if refined.element_tree is not None:
            html = element_tree_to_html(tree=refined.element_tree, theme=theme)
        else:
            # Generate HTML using template system
            html = generate_slide_html_with_branding(
                slide=enriched,
                theme=theme,
                colors=theme.colors,
                branding=branding,
                slide_number=slide_number,
                total_slides=total_slides,
            )
        
        self.state.slides_completed += 1
        
        return GeneratedSlide(
            order=refined.order,
            title=refined.title,
            theme_id=theme.id,
            rendered_html=html,
            element_tree=refined.element_tree,
            speaker_notes=refined.speaker_notes,
        )
    
    def _build_slide_html(self, slide: RefinedSlide) -> str:
        """Legacy fallback - Build HTML for a slide without templates."""
        bullets_html = "\n".join([
            f"<li>{point}</li>" for point in slide.bullet_points
        ])
        
        content_html = f"<ul>{bullets_html}</ul>"
        
        if slide.equation_svg:
            content_html += f'<div class="equation">{slide.equation_svg}</div>'
        
        if slide.diagram_svg:
            content_html += f'<div class="diagram">{slide.diagram_svg}</div>'
        
        if slide.image_url:
            content_html += f'<img src="{slide.image_url}" alt="{slide.image_alt or ""}">'
        
        return f"""<div class="slide slide-{slide.order}" data-template="{slide.template_type}">
    <div class="slide-header">
        <h1 class="slide-title">{slide.title}</h1>
    </div>
    <div class="slide-content">
        {content_html}
    </div>
</div>"""
    
    async def _run_qa(self):
        """
        Run Visual QA to grade slides using Gemini Vision.
        
        Flow:
        1. Render each slide HTML to PNG screenshot
        2. Send screenshots to Gemini Vision for grading
        3. Score 0-100 across 5 criteria (layout, typography, visibility, hierarchy, completeness)
        4. If any slide < 95%, retry up to 3 times
        5. After 3 retries, escalate to Helper agent
        """
        await self.emitter.stage_start("visual_qa")
        self.state.current_stage = "visual_qa"
        self.state.qa_loops += 1
        
        logger.info(f"Visual QA iteration {self.state.qa_loops}")
        
        # Get render client for screenshots
        from app.clients.render import RenderServiceClient
        render_client = RenderServiceClient()
        
        try:
            qa_results = []
            total_slides = len(self.state.generated_presentation.slides)
            
            for slide in self.state.generated_presentation.slides:
                await self.emitter.slide_progress(slide.order, total_slides, "grading")
                
                # Render slide to screenshot
                screenshot_result = await render_client.render_html_to_png(
                    html=slide.rendered_html,
                    width=1280,
                    height=720,
                )
                
                if screenshot_result.get("success", True) and screenshot_result.get("png_base64"):
                    # Grade with vision model
                    qa_result = await self._grade_slide_with_vision(
                        screenshot_base64=screenshot_result["png_base64"],
                        slide=slide,
                        iteration=self.state.qa_loops,
                    )
                else:
                    # Screenshot failed - mark as failed with error
                    logger.warning(f"Screenshot failed for slide {slide.order}: {screenshot_result.get('error')}")
                    qa_result = QAResult(
                        slide_order=slide.order,
                        score=0.0,
                        issues=[f"Screenshot failed: {screenshot_result.get('error', 'Unknown error')}"],
                        passed=False,
                        iterations=self.state.qa_loops,
                    )
                
                qa_results.append(qa_result)
                
                logger.info(f"Slide {slide.order}: score={qa_result.score}, passed={qa_result.passed}")
            
            # Calculate summary metrics
            avg_score = sum(r.score for r in qa_results) / len(qa_results) if qa_results else 0
            all_passed = all(r.passed for r in qa_results)
            failed_slides = [r for r in qa_results if not r.passed]
            
            self.state.qa_report = QAReport(
                session_id=self.state.session_id,
                slides=qa_results,
                average_score=avg_score,
                all_passed=all_passed,
                total_iterations=self.state.qa_loops,
            )
            
            # Log QA summary
            logger.info(f"QA complete: avg_score={avg_score:.1f}, all_passed={all_passed}, failed={len(failed_slides)}")
            
            # Check if we need to retry or escalate
            if not all_passed:
                if self.state.qa_loops < 3:
                    # Retry: regenerate failed slides
                    logger.info(f"Retrying {len(failed_slides)} failed slides...")
                    await self._regenerate_failed_slides(failed_slides)
                else:
                    # Escalate to Helper agent
                    logger.warning(f"QA failed after {self.state.qa_loops} iterations, escalating to Helper")
                    self.state.needs_helper = True
                    self.state.helper_context = {
                        "trigger": "qa_loop_exceeded",
                        "failed_slides": [
                            {"order": r.slide_order, "score": r.score, "issues": r.issues}
                            for r in failed_slides
                        ],
                        "total_iterations": self.state.qa_loops,
                    }
            
            await self.emitter.stage_complete("visual_qa", {
                "average_score": avg_score,
                "all_passed": all_passed,
                "failed_count": len(failed_slides),
                "iteration": self.state.qa_loops,
            })
            
        finally:
            await render_client.close()
    
    async def _grade_slide_with_vision(
        self,
        screenshot_base64: str,
        slide: GeneratedSlide,
        iteration: int,
    ) -> QAResult:
        """
        Use Gemini Vision to grade a slide screenshot.
        
        Criteria (each 0-20, total 0-100):
        1. Layout Quality - spacing, alignment, no overlaps
        2. Typography - readable fonts, proper hierarchy
        3. Content Visibility - all content visible, no cutoffs
        4. Visual Hierarchy - clear focus, logical flow
        5. Completeness - all expected content present
        """
        from google import genai
        from google.genai import types
        from app.core.config import settings
        
        # Construct the grading prompt
        grading_prompt = f"""Grade this slide screenshot on a 0-100 scale.

SLIDE INFO:
- Title: {slide.title}
- Order: {slide.order}
- Template: {slide.theme_id}

CRITERIA (each scored 0-20):
1. Layout Quality: Proper spacing, alignment, no overlapping elements
2. Typography: Readable font sizes, proper heading hierarchy
3. Content Visibility: All content visible, no cut-off text/images
4. Visual Hierarchy: Clear focus, important elements stand out
5. Completeness: All expected content present, no missing placeholders

RESPOND WITH JSON ONLY:
{{
    "layout_score": <0-20>,
    "typography_score": <0-20>,
    "visibility_score": <0-20>,
    "hierarchy_score": <0-20>,
    "completeness_score": <0-20>,
    "total_score": <0-100>,
    "issues": ["issue1", "issue2"],
    "suggestions": ["fix1", "fix2"]
}}"""

        try:
            # Import retry utility for transient API errors
            from app.clients.gemini.retry import gemini_retry
            
            # Create Gemini client with new SDK
            client = genai.Client(api_key=settings.gemini_api_key)
            
            # Define retry-wrapped API call (sync - new SDK doesn't use async)
            @gemini_retry(max_attempts=4, min_wait=1, max_wait=30)
            def call_vision_api():
                return client.models.generate_content(
                    model=settings.model_flash,
                    contents=[
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(text=grading_prompt),
                                types.Part(
                                    inline_data=types.Blob(
                                        mime_type="image/png",
                                        data=screenshot_base64,
                                    )
                                )
                            ]
                        )
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                    ),
                )
            
            # Generate grading with retry (run sync call in thread to keep async context)
            import asyncio
            import time
            vision_start = time.time()
            response = await asyncio.to_thread(call_vision_api)
            vision_elapsed_ms = int((time.time() - vision_start) * 1000)
            try:
                usage = extract_usage_from_response(response, model=settings.model_flash)
                self.metrics.record("visual_qa", usage, duration_ms=vision_elapsed_ms)
            except Exception:
                pass
            
            # Parse response
            import json
            result_text = response.text.strip()
            
            # Try to parse JSON
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                # Try to extract JSON from the response
                import re
                json_match = re.search(r'\{[\s\S]*\}', result_text)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise ValueError(f"Could not parse vision response: {result_text[:200]}")
            
            total_score = result.get("total_score", 0)
            issues = result.get("issues", [])
            
            return QAResult(
                slide_order=slide.order,
                score=float(total_score),
                issues=issues,
                passed=total_score >= 95,
                iterations=iteration,
            )
            
        except Exception as e:
            logger.error(f"Vision grading failed for slide {slide.order}: {e}")
            # Return a failing score with the error
            return QAResult(
                slide_order=slide.order,
                score=0.0,
                issues=[f"Vision grading error: {str(e)}"],
                passed=False,
                iterations=iteration,
            )
    
    async def _regenerate_failed_slides(self, failed_results: List[QAResult]):
        """
        Regenerate slides that failed QA with feedback.
        
        Uses the QA issues as context for the Generator to fix problems.
        """
        from app.themes import get_theme, UniversityBranding
        
        theme = get_theme(self.state.order_form.theme_id or "modern")
        branding = UniversityBranding()
        
        total_slides = len(self.state.generated_presentation.slides)
        failed_orders = {r.slide_order for r in failed_results}
        
        for result in failed_results:
            # Find the refined slide
            refined = next(
                (s for s in self.state.refined_content.slides if s.order == result.slide_order),
                None
            )
            if not refined:
                continue
            
            logger.info(f"Regenerating slide {result.slide_order} with QA feedback: {result.issues}")
            
            # Regenerate with feedback context
            new_generated = await self._generate_slide_html_with_template(
                refined=refined,
                theme=theme,
                branding=branding,
                slide_number=result.slide_order,
                total_slides=total_slides,
            )
            
            # Replace in presentation
            for i, slide in enumerate(self.state.generated_presentation.slides):
                if slide.order == result.slide_order:
                    self.state.generated_presentation.slides[i] = new_generated
                    break
    
    async def _run_helper(self):
        """
        Run Helper agent to fix failures after QA exhausted retries.
        
        The Helper:
        1. Analyzes failure context (which slides failed, what issues)
        2. Determines root cause and which stage to re-run
        3. Creates guardrail prompts to prevent same mistakes
        4. Re-runs the identified stage with guardrails
        5. If all retries exhausted, gracefully degrades
        
        Stage-Issue Mapping:
        - "Too much content" → Re-run Planner (reduce bullet points)
        - "Layout broken" → Re-run Generator (fix template/CSS)
        - "Equation not rendering" → Re-run Refiner (fix LaTeX)
        - "Missing diagram" → Re-run Refiner (regenerate Mermaid)
        """
        await self.emitter.stage_start("helper")
        self.state.current_stage = "helper"
        
        from app.crew.agents.helper import (
            create_helper_agent,
            create_fix_task,
            FailureContext,
            HelperDecision,
            build_guardrail_prompt,
        )
        from crewai import Crew
        
        # Get helper context from QA escalation
        helper_ctx = self.state.helper_context or {}
        failed_slides = helper_ctx.get("failed_slides", [])
        
        # Collect all issues across failed slides
        all_issues = []
        for slide_info in failed_slides:
            all_issues.extend(slide_info.get("issues", []))
        
        # Determine root cause and target stage
        root_stage = self._identify_root_stage(all_issues)
        
        logger.info(f"Helper analyzing {len(failed_slides)} failed slides, root stage: {root_stage}")
        
        # Check retry budget
        current_attempts = self.state.helper_attempts.get(root_stage, 0)
        max_attempts = 3  # Total retry budget
        
        if current_attempts >= max_attempts:
            # Budget exhausted - graceful degradation
            logger.warning(f"Retry budget exhausted for {root_stage}, proceeding with current slides")
            await self._graceful_degradation(failed_slides)
            await self.emitter.stage_complete("helper", {
                "action": "graceful_degradation",
                "reason": "retry_budget_exhausted",
            })
            return
        
        # Create failure context for Helper agent
        failure_context = FailureContext(
            failing_agent=root_stage,
            failure_type="qa_loop_exceeded",
            error_message=f"QA failed for slides: {[s['order'] for s in failed_slides]}",
            previous_attempts=current_attempts,
            qa_issues=all_issues[:10],  # Limit for context window
        )
        
        try:
            # Create Helper agent and task
            helper_agent = create_helper_agent()
            
            # Build available context
            available_context = {
                "order_form": self.state.order_form is not None,
                "skeleton": self.state.skeleton is not None,
                "planned_content": self.state.planned_content is not None,
                "refined_content": self.state.refined_content is not None,
                "generated_presentation": self.state.generated_presentation is not None,
            }
            
            # Original prompt for the failing stage (simplified)
            original_prompt = self._get_stage_prompt_summary(root_stage)
            
            task = create_fix_task(
                agent=helper_agent,
                failure_context=failure_context,
                original_prompt=original_prompt,
                available_context=available_context,
            )
            
            # Run Helper agent
            crew = Crew(
                agents=[helper_agent],
                tasks=[task],
                verbose=False,
            )
            from app.crew.utils.agent_execution import execute_crew_with_retry
            result = await execute_crew_with_retry(crew, "helper", session_id=self.state.session_id)
            
            # Parse Helper decision
            decision = self._parse_helper_decision(result)
            
            logger.info(f"Helper decision: {decision.action}")
            
            # Record attempt
            self.state.helper_attempts[root_stage] = current_attempts + 1
            
            # Execute decision
            if decision.action == "rerun_with_guardrails":
                # Re-run the identified stage with guardrails
                await self._rerun_stage_with_guardrails(
                    stage=root_stage,
                    guardrails=decision.guardrails or "",
                    failed_slides=failed_slides,
                )
                
                # Reset QA state for re-evaluation
                self.state.needs_helper = False
                self.state.qa_loops = 0  # Reset for fresh QA check
                
            elif decision.action == "escalate":
                # Graceful degradation with logging
                logger.warning(f"Helper escalated: {decision.escalate_reason}")
                await self._graceful_degradation(failed_slides)
                
            else:
                # Default: proceed with current state
                logger.info("Helper completed without action, proceeding")
            
            await self.emitter.stage_complete("helper", {
                "action": decision.action,
                "target_stage": root_stage,
            })
            
        except Exception as e:
            logger.error(f"Helper agent failed: {e}")
            # Fall back to graceful degradation
            await self._graceful_degradation(failed_slides)
            await self.emitter.stage_complete("helper", {
                "action": "error_fallback",
                "error": str(e),
            })
    
    def _identify_root_stage(self, issues: List[str]) -> str:
        """
        Analyze QA issues to determine which stage likely caused the problem.
        
        Returns: 'planner', 'refiner', or 'generator'
        """
        issues_text = " ".join(issues).lower()
        
        # Stage-Issue Mapping
        planner_keywords = [
            "too much content", "too many bullet", "too dense", 
            "overcrowded", "too long", "excessive"
        ]
        
        refiner_keywords = [
            "equation", "latex", "math", "diagram", "mermaid",
            "rendering", "citation", "image missing", "svg"
        ]
        
        generator_keywords = [
            "layout", "css", "overlap", "cut off", "template",
            "alignment", "spacing", "font", "broken"
        ]
        
        # Count keyword matches
        planner_score = sum(1 for kw in planner_keywords if kw in issues_text)
        refiner_score = sum(1 for kw in refiner_keywords if kw in issues_text)
        generator_score = sum(1 for kw in generator_keywords if kw in issues_text)
        
        # Return stage with highest score
        scores = {
            "planner": planner_score,
            "refiner": refiner_score,
            "generator": generator_score,
        }
        
        return max(scores, key=scores.get) if any(scores.values()) else "generator"
    
    def _get_stage_prompt_summary(self, stage: str) -> str:
        """Get a summary of the original prompt for a stage."""
        summaries = {
            "planner": "Create detailed slide content from skeleton with bullet points and placeholders",
            "refiner": "Convert placeholders to code, render assets, search citations",
            "generator": "Generate themed HTML slides with university branding",
        }
        return summaries.get(stage, "Process slide content")
    
    def _parse_helper_decision(self, result) -> "HelperDecision":
        """Parse the Helper agent's decision from result."""
        from app.crew.agents.helper import HelperDecision
        
        try:
            if hasattr(result, 'pydantic') and result.pydantic:
                return result.pydantic
            
            # Try to parse from raw output
            import json
            text = str(result.raw) if hasattr(result, 'raw') else str(result)
            
            import re
            json_match = re.search(r'\{[\s\S]*\}', text)
            if json_match:
                data = json.loads(json_match.group())
                return HelperDecision(**data)
            
        except Exception as e:
            logger.warning(f"Failed to parse Helper decision: {e}")
        
        # Default: escalate
        return HelperDecision(
            action="escalate",
            escalate_reason="Could not parse Helper decision",
        )
    
    async def _rerun_stage_with_guardrails(
        self,
        stage: str,
        guardrails: str,
        failed_slides: List[Dict],
    ):
        """Re-run a specific stage with guardrail context."""
        logger.info(f"Re-running {stage} with guardrails: {guardrails[:100]}...")
        
        # Store guardrails in state for the stage to use
        self.state.failure_context = {
            "guardrails": guardrails,
            "failed_slide_orders": [s["order"] for s in failed_slides],
        }
        
        # Re-run the appropriate stage
        if stage == "planner":
            await self._run_planner()
            await self._run_refiner()
            await self._run_generator()
        elif stage == "refiner":
            await self._run_refiner()
            await self._run_generator()
        elif stage == "generator":
            await self._run_generator()
    
    async def _graceful_degradation(self, failed_slides: List[Dict]):
        """
        Handle graceful degradation when all retries are exhausted.
        
        Logs the failure but returns the slides as-is, allowing
        the user to still get some output rather than nothing.
        """
        logger.warning("Graceful degradation: returning slides despite QA failures")
        
        # Log detailed failure info for debugging
        for slide_info in failed_slides:
            logger.warning(
                f"Slide {slide_info['order']}: score={slide_info.get('score', 0)}, "
                f"issues={slide_info.get('issues', [])}"
            )
        
        # Mark state as having degraded
        self.state.error_message = (
            f"QA passed with reduced standards due to retry exhaustion. "
            f"{len(failed_slides)} slides did not meet 95% threshold."
        )

# =============================================================================
# Flow Runner (High-Level API)
# =============================================================================

async def create_session(
    project_id: Optional[str] = None,
    mode: Optional[str] = None,
    topic: Optional[str] = None,
) -> FlowState:
    """Create a new generation session with optional metadata."""
    flow = SlideGenerationFlow()
    flow.state.project_id = project_id
    flow.state.mode = mode
    flow.state.topic = topic
    return flow.state


async def process_clarification(
    session_id: str,
    user_message: str,
    state: Optional[FlowState] = None,
) -> Dict[str, Any]:
    """Process a clarification message."""
    flow = SlideGenerationFlow(session_id=session_id)
    if state:
        flow.state = state
        try:
            flow.metrics.set_context(
                user_id=getattr(flow.state, "user_id", None),
                project_id=getattr(flow.state, "project_id", None),
                mode=getattr(flow.state, "mode", None),
            )
        except Exception:
            pass
    return await flow.process_clarification(user_message)


async def generate_outline(
    session_id: str,
    state: FlowState,
) -> Skeleton:
    """Generate the presentation outline."""
    flow = SlideGenerationFlow(session_id=session_id)
    flow.state = state
    try:
        flow.metrics.set_context(
            user_id=getattr(flow.state, "user_id", None),
            project_id=getattr(flow.state, "project_id", None),
            mode=getattr(flow.state, "mode", None),
        )
    except Exception:
        pass
    return await flow.generate_outline()


async def approve_outline(
    session_id: str,
    state: FlowState,
    modifications: Optional[List[Dict]] = None,
    modified_skeleton: Optional[Dict] = None,
) -> Skeleton:
    """Approve and optionally modify the outline."""
    flow = SlideGenerationFlow(session_id=session_id)
    flow.state = state
    try:
        flow.metrics.set_context(
            user_id=getattr(flow.state, "user_id", None),
            project_id=getattr(flow.state, "project_id", None),
            mode=getattr(flow.state, "mode", None),
        )
    except Exception:
        pass
    return await flow.approve_outline(modifications, modified_skeleton)


async def run_generation(
    session_id: str,
    state: FlowState,
    event_listener: Optional[Callable] = None,
) -> GeneratedPresentation:
    """Run the full generation pipeline."""
    emitter = FlowEventEmitter(session_id)
    if event_listener:
        emitter.add_listener(event_listener)
    
    flow = SlideGenerationFlow(session_id=session_id, event_emitter=emitter)
    flow.state = state
    try:
        flow.metrics.set_context(
            user_id=getattr(flow.state, "user_id", None),
            project_id=getattr(flow.state, "project_id", None),
            mode=getattr(flow.state, "mode", None),
        )
    except Exception:
        pass
    return await flow.run_generation()
