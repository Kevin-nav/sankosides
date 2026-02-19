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

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, AsyncGenerator
from uuid import UUID, uuid4
from datetime import datetime
import json
import asyncio
import os
import re
import threading
import base64

from app.models.schemas import (
    OrderForm,
    Skeleton,
    GeneratedPresentation,
    GatheredInfo,
    ClarificationMessage,
)
from app.models.slide_elements import SlideElementTree
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
from app.core.config import settings
from app.core.convex_client import get_convex_client
from app.core.posthog import capture as posthog_capture, build_common_props
from app.core.database import get_db, get_async_session
from app.services.storage import get_storage_service, PDFCacheService
from app.services.convex_service import get_convex_service
from app.clients.gemini.client import GeminiInteractionsClient
from lxml import html as lxml_html

logger = get_logger(__name__)

# Optional: manual spans to add high-value attributes (session_id/project_id) around background tasks.
try:
    from opentelemetry import trace  # type: ignore
    _tracer = trace.get_tracer(__name__)
except Exception:
    _tracer = None


def _token_metrics_for_posthog(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Return compact metrics suitable for PostHog properties:
    - totals
    - per-agent totals
    - per-agent per-model totals (aggregated from call history)
    """
    collector = MetricsCollector.get(session_id)
    if not collector:
        return None

    metrics = collector.get_metrics()
    data = metrics.to_dict()

    # Strip per-call history (too large/noisy for analytics).
    agents_in = data.get("agents", {}) or {}
    agents_out: Dict[str, Any] = {}

    # Walk the underlying call_history for full fidelity model aggregation.
    for agent_name, agent in metrics.agents.items():
        models: Dict[str, Dict[str, Any]] = {}
        for usage in agent.call_history:
            model = getattr(usage, "model", "") or "unknown"
            entry = models.get(model)
            if not entry:
                entry = {
                    "calls": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "thinking_tokens": 0,
                    "total_tokens": 0,
                    "cost_usd": 0.0,
                }
                models[model] = entry

            entry["calls"] += 1
            entry["input_tokens"] += int(getattr(usage, "input_tokens", 0) or 0)
            entry["output_tokens"] += int(getattr(usage, "output_tokens", 0) or 0)
            entry["thinking_tokens"] += int(getattr(usage, "thinking_tokens", 0) or 0)
            entry["total_tokens"] += int(getattr(usage, "total_tokens", 0) or 0)
            try:
                entry["cost_usd"] += float(usage.calculate_cost() or 0.0)
            except Exception:
                pass

        agents_out[agent_name] = {
            "calls": int(agent.calls or 0),
            "input_tokens": int(agent.total_input_tokens or 0),
            "output_tokens": int(agent.total_output_tokens or 0),
            "thinking_tokens": int(agent.total_thinking_tokens or 0),
            "total_tokens": int(agent.total_tokens or 0),
            "cost_usd": round(float(agent.total_cost_usd or 0.0), 6),
            "total_duration_ms": int(agent.total_duration_ms or 0),
            "avg_duration_ms": round(float(agent.avg_duration_ms or 0.0), 2),
            "models": {
                model: {
                    **vals,
                    "cost_usd": round(float(vals.get("cost_usd", 0.0)), 6),
                }
                for model, vals in models.items()
            },
        }

    totals = data.get("totals", {}) or {}
    flat: Dict[str, Any] = {
        "total_input_tokens": int(totals.get("input_tokens", 0) or 0),
        "total_output_tokens": int(totals.get("output_tokens", 0) or 0),
        "total_thinking_tokens": int(totals.get("thinking_tokens", 0) or 0),
        "total_tokens": int(totals.get("total_tokens", 0) or 0),
        "total_cost_usd": float(totals.get("cost_usd", 0.0) or 0.0),
        "total_api_calls": int(totals.get("api_calls", 0) or 0),
        "pipeline_duration_ms": totals.get("pipeline_duration_ms", None),
    }
    for agent_name, agent_vals in agents_out.items():
        safe_name = str(agent_name).strip().lower().replace(" ", "_")
        flat[f"agent_calls_{safe_name}"] = int(agent_vals.get("calls", 0) or 0)
        flat[f"agent_total_tokens_{safe_name}"] = int(agent_vals.get("total_tokens", 0) or 0)
        flat[f"agent_cost_usd_{safe_name}"] = float(agent_vals.get("cost_usd", 0.0) or 0.0)
        flat[f"agent_total_duration_ms_{safe_name}"] = int(agent_vals.get("total_duration_ms", 0) or 0)
        flat[f"agent_avg_duration_ms_{safe_name}"] = float(agent_vals.get("avg_duration_ms", 0.0) or 0.0)

    return {
        "totals": totals,
        "agents": agents_out,
        "flat": flat,
    }

router = APIRouter(prefix="/generation", tags=["generation"])


def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """
    Auth dependency for protecting endpoints that could leak cached document contents.

    If Firebase is configured (settings.firebase_project_id), we verify the Bearer token.
    Otherwise we still require a Bearer token to prevent unauthenticated enumeration.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid Authorization header")

    if getattr(settings, "firebase_project_id", None):
        try:
            from google.auth.transport.requests import Request as GoogleRequest
            from google.oauth2 import id_token as google_id_token

            claims = google_id_token.verify_firebase_token(
                token,
                GoogleRequest(),
                audience=settings.firebase_project_id,
            )
            return claims or {}
        except Exception:
            logger.warning("[AUTH] Token verification failed", exc_info=True)
            raise HTTPException(status_code=401, detail="Invalid auth token")

    # Best-effort: still gate on presence of a Bearer token.
    return {"token": token}


def _try_get_user_id_from_authorization(authorization: Optional[str]) -> Optional[str]:
    """
    Best-effort extraction of the Firebase UID from an Authorization header.

    In production, set `FIREBASE_PROJECT_ID` so we can verify ID tokens.
    """
    if not authorization:
        return None
    if not authorization.lower().startswith("bearer "):
        return None

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return None

    firebase_project_id = getattr(settings, "firebase_project_id", None)
    if firebase_project_id:
        try:
            from google.auth.transport.requests import Request as GoogleRequest
            from google.oauth2 import id_token as google_id_token

            claims = google_id_token.verify_firebase_token(
                token,
                GoogleRequest(),
                audience=firebase_project_id,
            ) or {}

            uid = claims.get("user_id") or claims.get("sub") or claims.get("uid")
            if isinstance(uid, str) and uid:
                return uid
        except Exception:
            return None

    # Optionally allow unverified extraction in local dev.
    allow_unverified = str(os.getenv("ALLOW_UNVERIFIED_JWT_USER_ID", "false")).strip().lower() in {"1", "true", "yes", "on"}
    if not allow_unverified:
        return None

    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        padding = "=" * (-len(payload_b64) % 4)
        payload_json = base64.urlsafe_b64decode((payload_b64 + padding).encode("utf-8")).decode("utf-8")
        claims = json.loads(payload_json) if payload_json else {}
        uid = claims.get("user_id") or claims.get("sub") or claims.get("uid")
        if isinstance(uid, str) and uid:
            return uid
    except Exception:
        return None

    return None


# =============================================================================
# Thread-Safe In-Memory Session Store
# =============================================================================

_sessions_lock = threading.RLock()  # Thread-safe lock for session access
_convex_session_persistence_enabled = (
    str(os.getenv("GENERATION_SESSION_PERSISTENCE", "true")).strip().lower()
    not in {"0", "false", "no", "off"}
) and bool(os.getenv("CONVEX_URL"))


def _flow_to_run_stage_and_status(flow_status: Any) -> tuple[str, str]:
    s = str(flow_status or "").strip().lower()
    if s in {"failed"}:
        return "failed", "failed"
    if s in {"completed"}:
        return "completed", "completed"
    if s in {"generating", "qa_in_progress"}:
        return "generating", "active"
    if s in {"clarification_complete", "awaiting_outline_approval", "outline_approved"}:
        return "blueprint", "active"
    return "clarifying", "active"


def _build_persistable_flow_state(state: FlowState) -> Dict[str, Any]:
    """
    Persist only resumability-critical fields.

    We intentionally skip heavy blobs (knowledge_base, planned/refined/generated slide payloads)
    to avoid oversized Convex documents.
    """
    payload = {
        "session_id": state.session_id,
        "user_id": state.user_id,
        "project_id": state.project_id,
        "mode": state.mode,
        "topic": state.topic,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "order_form": state.order_form,
        "skeleton": state.skeleton,
        "uploaded_files": state.uploaded_files,
        "conversation_history": state.conversation_history,
        "gathered_info": state.gathered_info,
        "selected_sections": state.selected_sections,
        "approved_related": state.approved_related,
        "declined_related": state.declined_related,
        "document_scoped": state.document_scoped,
        "pending_related_sections": state.pending_related_sections,
        "status": state.status,
        "current_stage": state.current_stage,
        "qa_loops": state.qa_loops,
        "max_qa_loops": state.max_qa_loops,
        "helper_attempts": state.helper_attempts,
        "failure_context": state.failure_context,
        "needs_helper": state.needs_helper,
        "helper_context": state.helper_context,
        "error_message": state.error_message,
        "slides_completed": state.slides_completed,
        "total_slides": state.total_slides,
    }
    return FlowState.model_validate(payload).model_dump(mode="json")


def _load_run_by_session_from_convex(session_id: str) -> Optional[Dict[str, Any]]:
    if not _convex_session_persistence_enabled:
        return None
    try:
        client = get_convex_client()
        run = client.query("generationRuns:getBySession", {"sessionId": session_id})
        return run if isinstance(run, dict) else None
    except Exception as exc:
        logger.warning(f"Convex session lookup failed for {session_id}: {exc}")
        return None


def _restore_state_from_run(session_id: str, run: Dict[str, Any]) -> Optional[FlowState]:
    runtime = run.get("runtime")
    if isinstance(runtime, dict):
        flow_state_raw = runtime.get("flow_state")
        if isinstance(flow_state_raw, dict):
            try:
                restored = FlowState.model_validate(flow_state_raw)
                if not restored.project_id and run.get("projectId"):
                    restored.project_id = str(run.get("projectId"))
                return restored
            except Exception as exc:
                logger.warning(f"Invalid runtime flow_state for session {session_id}: {exc}")

    # Backward-compat rebuild for older runs that predate backend runtime snapshots.
    try:
        rebuilt = FlowState(session_id=session_id)
        rebuilt.project_id = str(run.get("projectId")) if run.get("projectId") else None
        rebuilt.mode = str(run.get("mode")) if run.get("mode") else None

        stage = str(run.get("stage") or "").strip().lower()
        if stage == "completed":
            rebuilt.status = FlowStatus.COMPLETED
        elif stage == "failed":
            rebuilt.status = FlowStatus.FAILED
        elif stage == "generating":
            rebuilt.status = FlowStatus.GENERATING
        elif stage == "blueprint":
            rebuilt.status = FlowStatus.AWAITING_OUTLINE_APPROVAL
        else:
            rebuilt.status = FlowStatus.AWAITING_CLARIFICATION

        uploads = run.get("uploads")
        if isinstance(uploads, dict):
            file_hashes = uploads.get("file_hashes")
            if isinstance(file_hashes, list):
                rebuilt.uploaded_files = [{"file_hash": str(h)} for h in file_hashes if isinstance(h, str) and h.strip()]

        brief = run.get("brief")
        if isinstance(brief, dict):
            if isinstance(brief.get("topic"), str):
                rebuilt.topic = brief.get("topic")
            collected = brief.get("collectedData")
            if isinstance(collected, dict):
                _apply_wizard_data_to_state(rebuilt, collected)
            answered = brief.get("answeredQuestions")
            if isinstance(answered, list):
                for qa in answered:
                    if not isinstance(qa, dict):
                        continue
                    q = qa.get("question")
                    a = qa.get("answer")
                    if isinstance(q, str) and q.strip():
                        rebuilt.conversation_history.append(
                            ClarificationMessage(role="assistant", content=q.strip())
                        )
                    if isinstance(a, str) and a.strip():
                        rebuilt.conversation_history.append(
                            ClarificationMessage(role="user", content=a.strip())
                        )

        return rebuilt
    except Exception as exc:
        logger.warning(f"Failed to rebuild FlowState from Convex run for {session_id}: {exc}")
        return None


def _persist_session_to_convex(state: FlowState) -> None:
    if not _convex_session_persistence_enabled:
        return
    try:
        client = get_convex_client()
        run_stage, run_status = _flow_to_run_stage_and_status(state.status)
        payload: Dict[str, Any] = {
            "sessionId": state.session_id,
            "runtime": {
                "version": 1,
                "persisted_at": datetime.utcnow().isoformat(),
                "flow_state": _build_persistable_flow_state(state),
            },
            "mode": state.mode,
            "stage": run_stage,
            "status": run_status,
        }
        if state.project_id:
            payload["projectId"] = str(state.project_id)
        client.mutation("generationRuns:upsertRuntimeBySession", payload)
    except Exception as exc:
        logger.warning(f"Convex session persist failed for {state.session_id}: {exc}")


def _load_sessions() -> Dict[str, FlowState]:
    # Keep startup fast; sessions are lazy-restored from Convex on cache miss.
    return {}


_sessions: Dict[str, FlowState] = _load_sessions()


def get_session(session_id: str) -> FlowState:
    """Get session from store (thread-safe)."""
    with _sessions_lock:
        cached = _sessions.get(session_id)
        if cached is not None:
            return cached

    run = _load_run_by_session_from_convex(session_id)
    if run is not None:
        restored = _restore_state_from_run(session_id, run)
        if restored is not None:
            with _sessions_lock:
                _sessions[session_id] = restored
            return restored

    raise HTTPException(status_code=404, detail="Session not found")


def save_session(state: FlowState):
    """Save session to store (thread-safe)."""
    with _sessions_lock:
        state.updated_at = datetime.utcnow()
        _sessions[state.session_id] = state
    _persist_session_to_convex(state)


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


async def _get_cached_kb(cache_service: PDFCacheService, file_hash: str):
    """
    Shared helper for PDF cache lookups.

    Uses DB sessions so L3 cache can be consulted when enabled.
    """
    try:
        async for db_session in get_async_session():
            return await cache_service.get_cached(file_hash=file_hash, db_session=db_session)
    except Exception as e:
        logger.warning(f"PDF cache lookup failed for {file_hash[:16]}...: {e}")

    # Fallback: L2-only path via generic client argument
    try:
        return await cache_service.get_cached(file_hash=file_hash, client=get_db())
    except Exception as e:
        logger.warning(f"PDF cache fallback lookup failed for {file_hash[:16]}...: {e}")
        return None


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
    wizard_data: Optional[Dict[str, Any]] = None
    request_next_question: Optional[bool] = False
    field_key: Optional[str] = None


class ConfirmRequest(BaseModel):
    """Optional payload for deterministic wizard confirmations."""
    wizard_data: Optional[Dict[str, Any]] = None
    source: Optional[str] = None


def _normalize_emphasis_style(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    normalized = value.strip().lower()
    mapping = {
        "visual": "visual-heavy",
        "visual_heavy": "visual-heavy",
        "visual-heavy": "visual-heavy",
        "detailed": "detailed",
        "concise": "concise",
    }
    return mapping.get(normalized, normalized)


def _parse_slide_count_from_wizard(wizard_data: Dict[str, Any]) -> Optional[int]:
    slide_count = wizard_data.get("slideCount") or wizard_data.get("slide_count")
    if isinstance(slide_count, str):
        normalized = slide_count.strip().lower()
        if normalized.isdigit():
            slide_count = int(normalized)
        elif normalized == "auto":
            slide_count = None

    if isinstance(slide_count, int) and slide_count > 0:
        return slide_count

    slide_range = wizard_data.get("slideRange") or wizard_data.get("slide_range")
    if isinstance(slide_range, str):
        normalized_range = slide_range.strip().lower()
        if normalized_range == "auto":
            return None
        match = re.match(r"^\s*(\d+)\s*-\s*(\d+)\s*$", normalized_range)
        if match:
            low = int(match.group(1))
            high = int(match.group(2))
            if low > 0 and high >= low:
                return round((low + high) / 2)

    return None


def _is_wizard_setup_v2(source: Optional[str]) -> bool:
    return isinstance(source, str) and source.strip().lower() == "wizard_setup_v2"


def _apply_wizard_completion_fallbacks(state: FlowState) -> None:
    """
    Ensure deterministic wizard sessions are confirmable without conversational clarifier turns.
    """
    info = state.gathered_info or GatheredInfo()

    if not info.has_title:
        topic = (state.topic or "").strip()
        if topic:
            info.title = topic
            info.has_title = True
            if not info.key_topics:
                info.key_topics = [topic]

    if not info.has_focus_areas:
        scoped = [str(s).strip() for s in (state.selected_sections or []) if str(s).strip()]
        if scoped:
            info.focus_areas = scoped
            info.has_focus_areas = True
        elif info.title:
            info.focus_areas = [info.title]
            info.has_focus_areas = True

    if not info.has_slide_count:
        info.slide_count = info.slide_count or 10
        info.has_slide_count = True

    if not info.has_audience:
        info.audience = info.audience or "University students"
        info.has_audience = True

    state.gathered_info = info


def _apply_wizard_data_to_state(state: FlowState, wizard_data: Dict[str, Any]) -> None:
    """Hydrate gathered clarification info from wizard-collected values."""
    if not wizard_data:
        return

    info = state.gathered_info or GatheredInfo()

    topic = wizard_data.get("topic") or wizard_data.get("title")
    if isinstance(topic, str) and topic.strip():
        info.title = topic.strip()
        info.has_title = True
        if not info.key_topics:
            info.key_topics = [info.title]

    audience = wizard_data.get("audience") or wizard_data.get("target_audience")
    if isinstance(audience, str) and audience.strip():
        normalized_audience = audience.strip()
        audience_map = {
            "students": "University students",
            "mixed_academic": "Mixed academic audience",
            "technical": "Technical audience",
            "general": "General audience",
        }
        info.audience = audience_map.get(normalized_audience.lower(), normalized_audience)
        info.has_audience = True

    slide_count = _parse_slide_count_from_wizard(wizard_data)
    if isinstance(slide_count, int) and slide_count > 0:
        info.slide_count = slide_count
        info.has_slide_count = True

    sections = wizard_data.get("sections") or wizard_data.get("focus_areas")
    if isinstance(sections, list):
        normalized_sections = [str(s).strip() for s in sections if str(s).strip()]
        if normalized_sections:
            info.focus_areas = normalized_sections
            info.has_focus_areas = True
            # If document content is loaded, also mark flow-level document scoping.
            has_kb = bool(getattr(state, "knowledge_base", None) or getattr(state, "kb", None))
            if has_kb:
                state.selected_sections = normalized_sections
                state.document_scoped = True

    style = wizard_data.get("style") or wizard_data.get("emphasis_style")
    if isinstance(style, str):
        normalized_style = _normalize_emphasis_style(style)
        if normalized_style in {"detailed", "concise", "visual-heavy"}:
            info.emphasis_style = normalized_style
            info.has_emphasis_style = True

    tone = wizard_data.get("tone")
    if isinstance(tone, str):
        normalized_tone = tone.strip().lower()
        if normalized_tone in {"academic", "casual", "technical", "persuasive"}:
            info.tone = normalized_tone
            info.has_tone = True

    citation_style = wizard_data.get("citationStyle") or wizard_data.get("citation_style")
    if isinstance(citation_style, str):
        normalized_citation = citation_style.strip().lower()
        if normalized_citation in {"apa", "ieee", "harvard", "chicago"}:
            info.citation_style = normalized_citation
            info.has_citation_style = True

    references_placement = wizard_data.get("referencePlacement") or wizard_data.get("references_placement")
    if isinstance(references_placement, str):
        normalized_placement = references_placement.strip().lower().replace(" ", "_")
        if normalized_placement in {"distributed", "last_slide"}:
            info.references_placement = normalized_placement
            info.has_references_placement = True

    theme = wizard_data.get("theme")
    if isinstance(theme, str) and theme.strip():
        info.theme = theme.strip()
        info.has_theme = True

    special_requests = wizard_data.get("special_requests")
    if isinstance(special_requests, str) and special_requests.strip():
        info.special_requests = special_requests.strip()

    state.gathered_info = info


def _apply_field_answer_to_state(state: FlowState, field_key: Optional[str], answer: Optional[str]) -> None:
    """Apply single-field answers coming from wizard cards."""
    if not field_key or not isinstance(answer, str) or not answer.strip():
        return

    info = state.gathered_info or GatheredInfo()
    value = answer.strip()
    key = field_key.strip().lower()

    if key in {"title", "topic"}:
        info.title = value
        info.has_title = True
    elif key in {"target_audience", "audience"}:
        info.audience = value
        info.has_audience = True
    elif key in {"slide_count", "slidecount"}:
        if value.isdigit():
            info.slide_count = int(value)
            info.has_slide_count = True
    elif key in {"focus_areas", "sections"}:
        info.focus_areas = [value]
        info.has_focus_areas = True
    elif key in {"emphasis_style", "style"}:
        normalized_style = _normalize_emphasis_style(value)
        if normalized_style in {"detailed", "concise", "visual-heavy"}:
            info.emphasis_style = normalized_style
            info.has_emphasis_style = True
    elif key == "tone":
        normalized_tone = value.lower()
        if normalized_tone in {"academic", "casual", "technical", "persuasive"}:
            info.tone = normalized_tone
            info.has_tone = True
    elif key in {"citation_style", "citationstyle"}:
        normalized_citation = value.lower()
        if normalized_citation in {"apa", "ieee", "harvard", "chicago"}:
            info.citation_style = normalized_citation
            info.has_citation_style = True
    elif key in {"references_placement", "referenceplacement"}:
        normalized_placement = value.lower().replace(" ", "_")
        if normalized_placement in {"distributed", "last_slide"}:
            info.references_placement = normalized_placement
            info.has_references_placement = True
    elif key == "theme":
        info.theme = value
        info.has_theme = True
    elif key == "special_requests":
        info.special_requests = value

    state.gathered_info = info


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


class DocumentSectionPreview(BaseModel):
    """Compact section representation for UI scoping."""
    title: str
    preview: str
    page_range: str = ""
    visuals_count: int = 0


class DocumentSectionsRequest(BaseModel):
    file_hashes: List[str] = Field(default_factory=list)


class DocumentSectionsItem(BaseModel):
    file_hash: str
    filename: Optional[str] = None
    status: str  # completed | queued | processing | failed | missing
    sections_count: Optional[int] = None
    sections: Optional[List[DocumentSectionPreview]] = None
    error_message: Optional[str] = None


class DocumentSectionsResponse(BaseModel):
    documents: List[DocumentSectionsItem]


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


class PatchSlideRequest(BaseModel):
    """Patch a single slide in an already-generated presentation."""
    slide_order: int = Field(..., ge=1, description="1-indexed slide order")
    instruction: str = Field(..., min_length=1, max_length=4000, description="User instruction for the patch")
    keep_layout: bool = Field(default=True, description="Try to preserve layout/structure and only adjust content")


class PatchSlideResponse(BaseModel):
    session_id: str
    slide_order: int
    slide: Dict[str, Any]
    message: str


class PatchElementTreeRequest(BaseModel):
    """Persist an edited element tree for a single slide."""
    slide_order: int = Field(..., ge=1, description="1-indexed slide order")
    element_tree: SlideElementTree
    regenerate_html: bool = Field(
        default=True,
        description="If true, regenerate rendered_html from element_tree before saving",
    )


class PatchElementTreeResponse(BaseModel):
    session_id: str
    slide_order: int
    slide: Dict[str, Any]
    message: str


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/start", response_model=StartSessionResponse)
async def start_session_endpoint(
    project_id: Optional[str] = None,
    mode: Optional[str] = None,
    topic: Optional[str] = None,
    files: Optional[List[UploadFile]] = File(None),
    authorization: Optional[str] = Header(default=None),
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
    state.user_id = _try_get_user_id_from_authorization(authorization) or state.user_id
    save_session(state)
    
    # If files are provided, upload to R2 and run synthesis
    if files:
        logger.info(f"Received {len(files)} files for synthesis. Starting session {state.session_id}")
        
        storage = get_storage_service()
        cache_service = PDFCacheService()
        
        # Track uploaded files and cache hits
        uploaded_files = []
        cache_hits = 0
        
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
                cached_kb = await _get_cached_kb(cache_service, file_hash)
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
        cached_kb = await _get_cached_kb(cache_service, file_hash)
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


@router.post("/document-sections", response_model=DocumentSectionsResponse)
async def get_document_sections(
    request: DocumentSectionsRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """
    Return extracted document section structure for a list of file hashes.

    This is intended for the frontend "scope" UI so users can select which
    parts of each PDF to use. It only returns cached sections (no reprocessing).
    """
    cache_service = PDFCacheService()
    documents: List[DocumentSectionsItem] = []

    for file_hash in request.file_hashes:
        file_hash = str(file_hash).strip()
        if not file_hash:
            continue

        cached_kb = await _get_cached_kb(cache_service, file_hash)
        if cached_kb and getattr(cached_kb, "sections", None):
            sections = []
            for section in cached_kb.sections:
                content = getattr(section, "content", "") or ""
                preview = " ".join(content.split())
                if len(preview) > 220:
                    preview = preview[:220].rstrip() + "..."
                visuals = getattr(section, "visuals", None) or []
                sections.append(
                    DocumentSectionPreview(
                        title=getattr(section, "title", "") or "Untitled section",
                        preview=preview,
                        page_range=getattr(section, "page_range", "") or "",
                        visuals_count=len(visuals),
                    )
                )

            filename = ""
            try:
                if cached_kb.sections:
                    filename = getattr(cached_kb.sections[0], "document_name", "") or ""
            except Exception:
                filename = ""

            documents.append(
                DocumentSectionsItem(
                    file_hash=file_hash,
                    filename=filename or None,
                    status="completed",
                    sections_count=len(sections),
                    sections=sections,
                )
            )
            continue

        job = get_processing_status(file_hash)
        if job:
            documents.append(
                DocumentSectionsItem(
                    file_hash=file_hash,
                    filename=job.filename,
                    status=job.status.value,
                    sections_count=job.sections_count,
                    error_message=job.error_message,
                )
            )
            continue

        documents.append(
            DocumentSectionsItem(
                file_hash=file_hash,
                status="missing",
            )
        )

    return DocumentSectionsResponse(documents=documents)


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
            cached_kb = await _get_cached_kb(cache_service, file_hash)
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
        # Sync wizard-provided context into gathered info before asking the agent
        if request.wizard_data:
            _apply_wizard_data_to_state(state, request.wizard_data)

        # Sync single-card answer payloads if present
        _apply_field_answer_to_state(state, request.field_key, request.message)

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
                    cached_kb = await _get_cached_kb(cache_service, file_hash)
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
async def confirm_clarification(
    session_id: str,
    background_tasks: BackgroundTasks,
    request: Optional[ConfirmRequest] = None,
):
    """
    Confirm the gathered clarification info.
    
    Called when user clicks "Approve" button on the confirmation UI.
    Finalizes the OrderForm and moves to CLARIFICATION_COMPLETE status.
    
    Automatically triggers background outline generation.
    """
    state = get_session(session_id)
    if request and request.wizard_data:
        _apply_wizard_data_to_state(state, request.wizard_data)
    if request and _is_wizard_setup_v2(request.source):
        _apply_wizard_completion_fallbacks(state)
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
async def start_generation(
    session_id: str,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(default=None),
):
    """
    Start the generation pipeline.
    
    This runs asynchronously in the background.
    Use /stream/{session_id} for real-time progress.
    Use /status/{session_id} to poll status.
    """
    state = get_session(session_id)
    if not getattr(state, "user_id", None):
        state.user_id = _try_get_user_id_from_authorization(authorization) or state.user_id
        save_session(state)
    
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
    mode = str(getattr(state, "mode", "") or "")
    
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
        if _tracer:
            with _tracer.start_as_current_span(
                "sanko.generation.run_generation",
                attributes={
                    "sanko.session_id": session_id,
                    "sanko.project_id": str(project_id) if project_id else "",
                    "sanko.total_slides": int(getattr(state, "total_slides", 0) or 0),
                    "sanko.mode": mode,
                },
            ):
                await run_generation(session_id, state)
        else:
            await run_generation(session_id, state)
        save_session(state)

        # PostHog: token usage per agent for pricing analysis.
        distinct_id = str(getattr(state, "user_id", "") or "") or (str(project_id) if project_id else session_id)
        metrics_payload = _token_metrics_for_posthog(session_id)
        if metrics_payload:
            posthog_capture(
                event="generation_token_metrics",
                distinct_id=distinct_id,
                properties=build_common_props(
                    session_id=session_id,
                    project_id=str(project_id) if project_id else None,
                    mode=mode or None,
                    status=str(getattr(state, "status", "") or ""),
                    total_slides=int(getattr(state, "total_slides", 0) or 0),
                    **({"$groups": {"project": str(project_id)}} if project_id else {}),
                    **(metrics_payload.get("flat", {}) or {}),
                    metrics=metrics_payload,
                ),
            )
        
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

        # PostHog: failure + partial token metrics (if any).
        distinct_id = str(getattr(state, "user_id", "") or "") or (str(project_id) if project_id else session_id)
        metrics_payload = _token_metrics_for_posthog(session_id)
        posthog_capture(
            event="generation_failed_token_metrics",
            distinct_id=distinct_id,
            properties=build_common_props(
                session_id=session_id,
                project_id=str(project_id) if project_id else None,
                mode=mode or None,
                status=str(getattr(state, "status", "") or ""),
                error_message=state.error_message,
                **({"$groups": {"project": str(project_id)}} if project_id else {}),
                **(metrics_payload.get("flat", {}) or {}) if metrics_payload else {},
                metrics=metrics_payload,
            ),
        )
        
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
        
        project_id = getattr(state, "project_id", None)
        mode = str(getattr(state, "mode", "") or "")
        if _tracer:
            with _tracer.start_as_current_span(
                "sanko.generation.generate_outline",
                attributes={
                    "sanko.session_id": session_id,
                    "sanko.project_id": str(getattr(state, "project_id", "") or ""),
                    "sanko.mode": mode,
                },
            ):
                await generate_outline(session_id, state)
        else:
            await generate_outline(session_id, state)
        
        logger.info(f"[OUTLINE_TASK] State AFTER generate_outline: status={state.status}, skeleton={'SET' if state.skeleton else 'NONE'}")
        if state.skeleton:
            logger.info(f"[OUTLINE_TASK] Skeleton has {len(state.skeleton.slides)} slides")
        
        save_session(state)
        logger.info(f"[OUTLINE_TASK] save_session() completed for session {session_id}")

        # PostHog: outline stage token metrics.
        distinct_id = str(getattr(state, "user_id", "") or "") or (str(project_id) if project_id else session_id)
        metrics_payload = _token_metrics_for_posthog(session_id)
        if metrics_payload:
            posthog_capture(
                event="outline_token_metrics",
                distinct_id=distinct_id,
                properties=build_common_props(
                    session_id=session_id,
                    project_id=str(project_id) if project_id else None,
                    mode=mode or None,
                    status=str(getattr(state, "status", "") or ""),
                    slides_planned=int(len(state.skeleton.slides)) if state.skeleton and getattr(state.skeleton, "slides", None) else None,
                    **({"$groups": {"project": str(project_id)}} if project_id else {}),
                    **(metrics_payload.get("flat", {}) or {}),
                    metrics=metrics_payload,
                ),
            )
        
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


def _strip_markdown_code_fences(text: str) -> str:
    """Gemini sometimes returns ```html fenced blocks; normalize to raw HTML."""
    if not isinstance(text, str):
        return ""
    stripped = text.strip()
    match = re.match(r"^```(?:html)?\s*([\s\S]*?)\s*```$", stripped, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return stripped


def sanitize_slide_html(raw_html: str) -> str:
    """
    Best-effort sanitizer/validator for LLM-produced slide HTML.

    Policy:
    - Strip disallowed tags: script, iframe, object, embed, noscript
    - Strip inline event handler attributes (on*)
    - Strip javascript: URLs
    - Strip external resource links (http/https///) from src/href-like attrs
    - Strip external CSS urls embedded in style attributes (url(http...))

    Raises:
        ValueError if parsing fails or the sanitized output is empty.
    """
    if not isinstance(raw_html, str):
        raise ValueError("HTML must be a string")

    html_in = raw_html.strip()
    if not html_in:
        raise ValueError("HTML is empty")

    disallowed_tags = {"script", "iframe", "object", "embed", "noscript"}
    url_attrs = {"src", "href", "xlink:href", "poster", "data"}

    def _classify_url(value: str) -> str:
        v = (value or "").strip()
        if not v:
            return ""
        v_lower = v.lower()
        if v_lower.startswith("javascript:"):
            return "javascript"
        if v_lower.startswith("http://") or v_lower.startswith("https://") or v_lower.startswith("//"):
            return "external"
        return ""

    try:
        root = lxml_html.fromstring(html_in)
    except Exception as e:
        raise ValueError(f"Failed to parse HTML: {e}")

    # Work on a stable list because we may drop trees during iteration.
    elements = list(root.iter())

    for el in elements:
        if not isinstance(el.tag, str):
            continue

        tag = el.tag.lower()
        if tag in disallowed_tags:
            el.drop_tree()
            continue

        # Remove event handler attributes and unsafe/external URLs
        for attr in list(el.attrib.keys()):
            attr_l = attr.lower()
            val = el.attrib.get(attr, "")

            if attr_l.startswith("on"):
                del el.attrib[attr]
                continue

            # Remove JS or external URLs for url-like attrs
            if attr_l in url_attrs or attr_l.endswith(":href"):
                classification = _classify_url(val)
                if classification in {"javascript", "external"}:
                    del el.attrib[attr]
                    # For elements whose whole purpose is the external resource, drop them.
                    if tag in {"img", "source", "video", "audio", "track"} and attr_l == "src":
                        el.drop_tree()
                        continue
                    if tag == "link" and attr_l == "href":
                        el.drop_tree()
                continue

            # Strip external resource URLs embedded in inline styles.
            if attr_l == "style":
                # Basic guard: remove styles that attempt to fetch remote resources.
                if re.search(r"url\(\s*['\"]?\s*(https?:)?//", val, flags=re.IGNORECASE):
                    del el.attrib[attr]
                continue

    # Sanitize <style> tags for remote @import (strip those lines).
    for style_el in root.xpath(".//style"):
        if not isinstance(style_el.tag, str):
            continue
        text = style_el.text or ""
        if not text:
            continue
        if re.search(r"@import\s+url\(\s*['\"]?\s*(https?:)?//", text, flags=re.IGNORECASE):
            cleaned_lines = []
            for line in text.splitlines():
                if re.search(r"@import\s+url\(\s*['\"]?\s*(https?:)?//", line, flags=re.IGNORECASE):
                    continue
                cleaned_lines.append(line)
            style_el.text = "\n".join(cleaned_lines)

    # Final hard check: ensure disallowed tags are not present anymore.
    for bad in disallowed_tags:
        if root.xpath(f".//{bad}"):
            raise ValueError(f"Disallowed tag present after sanitization: <{bad}>")

    sanitized = lxml_html.tostring(root, encoding="unicode", method="html")
    if not sanitized or not sanitized.strip():
        raise ValueError("Sanitized HTML is empty")

    return sanitized


@router.post("/patch-slide/{session_id}", response_model=PatchSlideResponse)
async def patch_slide(session_id: str, request: PatchSlideRequest):
    """
    Patch a single slide's HTML in place.

    This is intentionally lightweight: we do not re-run the full pipeline.
    """
    state = get_session(session_id)

    if state.status not in [FlowStatus.COMPLETED, "completed"]:
        raise HTTPException(status_code=400, detail=f"Cannot patch slides unless generation is complete. Status: {state.status}")

    if not state.generated_presentation or not getattr(state.generated_presentation, "slides", None):
        raise HTTPException(status_code=500, detail="No generated presentation found to patch")

    slide = next((s for s in state.generated_presentation.slides if getattr(s, "order", None) == request.slide_order), None)
    if not slide:
        raise HTTPException(status_code=404, detail=f"Slide {request.slide_order} not found")

    if not settings.gemini_api_key:
        raise HTTPException(status_code=503, detail="Gemini API key not configured")

    original_html = getattr(slide, "rendered_html", "") or ""
    if not original_html.strip():
        raise HTTPException(status_code=500, detail="Slide has no rendered_html to patch")

    layout_rule = (
        "Preserve the existing layout and structure as much as possible; only change what is necessary."
        if request.keep_layout
        else "You may change layout/structure if it helps satisfy the instruction."
    )

    system_instruction = (
        "You are an expert HTML slide editor. You will receive a complete HTML document for a single slide.\n"
        "Apply the user's instruction and return ONLY the updated complete HTML document.\n"
        "Do not wrap your answer in markdown. Do not include explanations.\n"
        "Do not add external network dependencies (no remote JS/CSS). Keep it self-contained.\n"
        f"{layout_rule}"
    )

    prompt = (
        "Existing slide HTML:\n"
        "```html\n"
        f"{original_html}\n"
        "```\n\n"
        "Instruction:\n"
        f"{request.instruction}\n\n"
        "Return only the updated complete HTML document."
    )

    try:
        client = GeminiInteractionsClient(api_key=settings.gemini_api_key)
        result = await client.generate_with_thinking(
            prompt=prompt,
            model=settings.model_flash,
            system_instruction=system_instruction,
            thinking_level=settings.thinking_level_low,
        )
        updated_html = _strip_markdown_code_fences(result.get("response", ""))
    except Exception as e:
        logger.exception("[PATCH_SLIDE] Gemini call failed")
        raise HTTPException(status_code=500, detail="Failed to patch slide")

    try:
        updated_html = sanitize_slide_html(updated_html)
    except ValueError as e:
        logger.warning(
            f"[PATCH_SLIDE] Rejected patched HTML for session={session_id[:8]}... slide={request.slide_order}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=400, detail="Invalid patched HTML")

    if len(updated_html.strip()) < 50:
        raise HTTPException(status_code=500, detail="Patched HTML was empty or invalid")

    slide.rendered_html = updated_html
    save_session(state)

    # Best-effort persistence to Convex project slidesData.
    project_id = getattr(state, "project_id", None)
    if project_id:
        try:
            client = get_db()
            slides_data = state.generated_presentation.model_dump()
            await asyncio.wait_for(
                asyncio.to_thread(
                    client.mutation,
                    "projects:update",
                    {"id": project_id, "slidesData": slides_data, "status": "completed"},
                ),
                timeout=10.0,
            )
        except Exception as e:
            logger.warning(f"[PATCH_SLIDE] Failed to persist patched slide to Convex: {e}")

    return PatchSlideResponse(
        session_id=session_id,
        slide_order=request.slide_order,
        slide=slide.model_dump(),
        message="Slide patched successfully.",
    )


@router.patch("/patch-element-tree/{session_id}", response_model=PatchElementTreeResponse)
async def patch_element_tree(session_id: str, request: PatchElementTreeRequest):
    """
    Persist a single slide's edited element tree.

    This keeps Convex slidesData in sync with backend session state.
    """
    state = get_session(session_id)

    if state.status not in [FlowStatus.COMPLETED, "completed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot patch element trees unless generation is complete. Status: {state.status}",
        )

    if not state.generated_presentation or not getattr(state.generated_presentation, "slides", None):
        raise HTTPException(status_code=500, detail="No generated presentation found to patch")

    slide = next(
        (s for s in state.generated_presentation.slides if getattr(s, "order", None) == request.slide_order),
        None,
    )
    if not slide:
        raise HTTPException(status_code=404, detail=f"Slide {request.slide_order} not found")

    slide.element_tree = request.element_tree

    if request.regenerate_html:
        try:
            from app.templates.html_generator import element_tree_to_html
            from app.themes import get_theme

            theme_id = getattr(slide, "theme_id", None) or getattr(state.order_form, "theme_id", "modern")
            theme = get_theme(theme_id or "modern")
            slide.rendered_html = element_tree_to_html(tree=request.element_tree, theme=theme)
        except Exception as e:
            logger.warning(f"[PATCH_ELEMENT_TREE] HTML regeneration failed for session={session_id[:8]}...: {e}")

    save_session(state)

    # Best-effort persistence to Convex project slidesData.
    project_id = getattr(state, "project_id", None)
    if project_id:
        try:
            client = get_db()
            slides_data = state.generated_presentation.model_dump()
            await asyncio.wait_for(
                asyncio.to_thread(
                    client.mutation,
                    "projects:update",
                    {"id": project_id, "slidesData": slides_data, "status": "completed"},
                ),
                timeout=10.0,
            )
        except Exception as e:
            logger.warning(f"[PATCH_ELEMENT_TREE] Failed to persist to Convex: {e}")

    return PatchElementTreeResponse(
        session_id=session_id,
        slide_order=request.slide_order,
        slide=slide.model_dump(),
        message="Element tree patched successfully.",
    )


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

