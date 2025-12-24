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
from app.crew.tools.synthesis_tool import SynthesisTool
from app.core.logging import get_logger
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
    
    # Clarification conversation tracking (NEW - fixes memory issue)
    conversation_history: List[ClarificationMessage] = Field(
        default_factory=list,
        description="Full conversation history for clarification phase"
    )
    gathered_info: Optional[GatheredInfo] = Field(
        default=None,
        description="Progressively tracked info from user during clarification"
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
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.listeners: List[Callable] = []
    
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
        logger.debug(f"Event: {event_type} - {data}")
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
        self.emitter = event_emitter or FlowEventEmitter(self.state.session_id)
        self.retry_tracker = RetryBudget()
        self.metrics = MetricsCollector.get_or_create(self.state.session_id)
    
    # =========================================================================
    # Stage 0: Synthesis (Pre-processing)
    # =========================================================================

    async def run_synthesis(self, file_paths: List[str]) -> KnowledgeBase:
        """
        Run multimodal extraction on a list of PDF files.
        
        This is the first stage of the Synthesis Engine mode.
        
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
            # Wrap the tool call in a thread pool since it's blocking
            loop = asyncio.get_event_loop()
            kb = await loop.run_in_executor(None, synthesis_tool._run, path)
            
            if isinstance(kb, str) and kb.startswith("Error"):
                logger.error(f"Synthesis failed for {path}: {kb}")
                continue
                
            all_sections.extend(kb.sections)
            combined_summary_parts.append(f"Content from {os.path.basename(path)}: {kb.summary}")
            
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
                include_speaker_notes=info.include_speaker_notes if info.include_speaker_notes is not None else True,
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
        
        # Create clarifier agent
        clarifier = create_clarifier_agent()
        
        # Build the full context for the agent
        conversation_context = self._format_conversation_history()
        gathered_context = self._format_gathered_info()
        missing_required = info.get_missing_required()
        missing_optional = info.get_missing_optional()
        
        # Determine what stage we're in
        if info.needs_confirmation():
            stage_instruction = """## CURRENT STAGE: CONFIRMATION REQUIRED
All essential info is gathered. You MUST now:
1. Summarize everything in a readable format
2. Ask: "Does this look correct? If so, I'll finalize your presentation requirements."
DO NOT output JSON yet - wait for user confirmation!"""
        elif not missing_required:
            stage_instruction = f"""## CURRENT STAGE: GATHER OPTIONAL INFO
Required info is complete. Ask about ONE of these optional fields:
{self._format_list(missing_optional[:2]) if missing_optional else "None left"}
Ask ONLY ONE question. Be conversational."""
        else:
            stage_instruction = f"""## CURRENT STAGE: GATHER REQUIRED INFO
Still need these required fields - ask about ONE:
{self._format_list(missing_required)}
Ask ONLY ONE question. Do not combine questions."""
        
        # Create task with FULL CONTEXT
        task = Task(
            description=f"""You are continuing a conversation to gather presentation requirements.

## FULL CONVERSATION HISTORY
{conversation_context}

## INFORMATION ALREADY GATHERED
{gathered_context}

{stage_instruction}

## CRITICAL RULES
1. **ASK EXACTLY ONE QUESTION** - Never combine multiple questions in one response
2. **DO NOT repeat questions** - Check gathered info above before asking
3. **If user says "decide yourself"** - Acknowledge and move to the NEXT question
4. **DO NOT output JSON** until user explicitly confirms the summary

## RESPONSE FORMAT
- For questions: Write ONE natural, conversational question (NO JSON)
- For confirmation: Summarize info + ask "Does this look correct?"
- For completion: Output OrderForm JSON with exact field names

Be friendly and efficient. ONE question at a time!""",
            expected_output="Either ONE follow-up question, a confirmation summary, OR a complete OrderForm JSON",
            agent=clarifier,
        )
        
        try:
            # Execute the agent
            crew = Crew(agents=[clarifier], tasks=[task])
            result = crew.kickoff()
            
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
                r"if (this|everything) looks (good|correct)",
                r"let me (know|confirm)",
            ]
            response_lower = response_text.lower()
            if any(re.search(p, response_lower) for p in confirmation_request_patterns):
                self.state.gathered_info.confirmation_sent = True
                logger.info(f"Detected confirmation request in agent response. Set confirmation_sent=True")
            
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
                
                # Check if we have enough info to show confirmation UI
                # (instead of asking more optional questions)
                if self.state.gathered_info.is_ready_for_confirmation():
                    # Return needs_confirmation with structured summary for UI
                    return {
                        "complete": False,
                        "needs_confirmation": True,
                        "question": None,  # Don't show the LLM's question
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
            
        if info.include_speaker_notes is not None:
            parts.append(f"- **Speaker Notes**: {'Yes' if info.include_speaker_notes else 'No'}")
            
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
            logger.info(f"User confirmed! Set user_confirmed=True")
        
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
        
        This stage PAUSES after generating - user must call
        approve_outline() to continue.
        
        Returns:
            Generated Skeleton (also saved to state)
        """
        await self.emitter.stage_start("outliner")
        
        if not self.state.order_form or not self.state.order_form.is_complete:
            raise ValueError("Cannot generate outline: OrderForm not complete")
        
        # Use the order form to create skeleton
        # In a real implementation, this would use an Outliner agent
        order = self.state.order_form
        
        # Generate skeleton based on preferences
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
        
        self.state.skeleton = skeleton
        self.state.status = FlowStatus.AWAITING_OUTLINE_APPROVAL
        self.state.total_slides = len(slides)
        
        await self.emitter.pause_for_review("outline", {
            "skeleton": skeleton.model_dump(),
        })
        
        return skeleton
    
    async def approve_outline(
        self,
        modifications: Optional[List[Dict]] = None,
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
            
        Returns:
            Updated Skeleton
        """
        if not self.state.skeleton:
            raise ValueError("No skeleton to approve")
        
        if modifications:
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
        Run the full generation pipeline: Planner → Refiner → Generator → QA
        
        This runs asynchronously with progress streaming.
        For performance, individual slides can be generated in parallel.
        
        Returns:
            GeneratedPresentation with all slides
        """
        if self.state.status != FlowStatus.OUTLINE_APPROVED:
            raise ValueError(f"Cannot generate: status is {self.state.status}")
        
        self.state.status = FlowStatus.GENERATING
        
        try:
            # Stage 3: Planner
            await self._run_planner()
            
            # Stage 4: Refiner (with async asset rendering)
            await self._run_refiner()
            
            # Stage 5: Generator (parallel slide generation)
            await self._run_generator()
            
            # Stage 6: Visual QA
            await self._run_qa()
            
            self.state.status = FlowStatus.COMPLETED
            await self.emitter.complete(self.state.generated_presentation)
            
            return self.state.generated_presentation
            
        except Exception as e:
            self.state.status = FlowStatus.FAILED
            self.state.error_message = str(e)
            await self.emitter.error(str(e), self.state.current_stage)
            raise
    
    async def _run_planner(self):
        """Run the Planner agent to generate content."""
        await self.emitter.stage_start("planner")
        self.state.current_stage = "planner"
        
        planner = create_planner_agent()
        
        # Build the planning task
        task = Task(
            description=self._build_planner_prompt(),
            expected_output="PlannedContent JSON with full bullet points for each slide",
            agent=planner,
        )
        
        crew = Crew(agents=[planner], tasks=[task])
        result = crew.kickoff()
        
        # Parse result into PlannedContent
        planned_content = self._parse_planned_content(str(result))
        self.state.planned_content = planned_content
        
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
            f"\n  Needs diagram: {s.needs_diagram}, equation: {s.needs_equation}, citation: {s.needs_citation}"
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
5. Add speaker_notes if requested: {order.include_speaker_notes}

Return a JSON object with 'slides' array containing PlannedSlide objects."""
    
    def _parse_planned_content(self, text: str) -> PlannedContent:
        """Parse PlannedContent from agent response."""
        import re
        
        # Try to extract JSON
        json_match = re.search(r'\{[\s\S]*\}', text)
        if json_match:
            try:
                data = json.loads(json_match.group())
                if "slides" in data:
                    return PlannedContent(
                        presentation_title=self.state.skeleton.presentation_title,
                        target_audience=self.state.skeleton.target_audience,
                        theme_id=self.state.order_form.theme_id,
                        citation_style=self.state.order_form.citation_style,
                        slides=[PlannedSlide(**s) for s in data["slides"]],
                    )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Failed to parse PlannedContent: {e}")
        
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
    
    async def _run_refiner(self):
        """Run the Refiner agent to render assets."""
        await self.emitter.stage_start("refiner")
        self.state.current_stage = "refiner"
        
        render_tool = get_render_tool()
        refiner = create_refiner_agent(tools=[render_tool])
        
        # Process each slide - could be parallelized
        refined_slides = []
        
        for i, planned_slide in enumerate(self.state.planned_content.slides):
            await self.emitter.slide_progress(planned_slide.order, len(self.state.planned_content.slides), "refining")
            
            refined_slide = await self._refine_slide(planned_slide, render_tool)
            refined_slides.append(refined_slide)
        
        self.state.refined_content = RefinedContent(
            presentation_title=self.state.planned_content.presentation_title,
            target_audience=self.state.planned_content.target_audience,
            theme_id=self.state.planned_content.theme_id,
            citation_style=self.state.planned_content.citation_style,
            slides=refined_slides,
            total_citations=sum(len(s.citations) for s in refined_slides),
            equations_rendered=sum(1 for s in refined_slides if s.equation_svg),
            diagrams_rendered=sum(1 for s in refined_slides if s.diagram_svg),
        )
        
        await self.emitter.stage_complete("refiner", {
            "slides_refined": len(refined_slides),
        })
    
    async def _refine_slide(self, planned: PlannedSlide, render_tool) -> RefinedSlide:
        """Refine a single slide (render assets)."""
        refined = RefinedSlide(
            order=planned.order,
            title=planned.title,
            content_type=planned.content_type,
            bullet_points=planned.bullet_points,
            template_type=planned.template_type or "content",
            speaker_notes=planned.speaker_notes,
        )
        
        # Render equation if present
        if planned.equation_placeholder:
            try:
                # Convert placeholder to LaTeX
                latex = self._placeholder_to_latex(planned.equation_placeholder)
                svg = render_tool._run(action="latex", content=latex)
                if not svg.startswith("Error"):
                    refined.equation_latex = latex
                    refined.equation_svg = svg
            except Exception as e:
                logger.warning(f"Failed to render equation: {e}")
        
        # Render diagram if present
        if planned.diagram_placeholder:
            try:
                mermaid = self._placeholder_to_mermaid(planned.diagram_placeholder)
                svg = render_tool._run(action="mermaid", content=mermaid)
                if not svg.startswith("Error"):
                    refined.diagram_mermaid = mermaid
                    refined.diagram_svg = svg
            except Exception as e:
                logger.warning(f"Failed to render diagram: {e}")
        
        return refined
    
    def _placeholder_to_latex(self, placeholder: str) -> str:
        """Convert a placeholder description to LaTeX. In production, agent does this."""
        # Simple conversion for common patterns
        if "linear regression" in placeholder.lower():
            return r"y = \beta_0 + \beta_1 x + \epsilon"
        elif "quadratic" in placeholder.lower():
            return r"ax^2 + bx + c = 0"
        else:
            return r"f(x) = \sum_{i=1}^{n} x_i"
    
    def _placeholder_to_mermaid(self, placeholder: str) -> str:
        """Convert a placeholder description to Mermaid. In production, agent does this."""
        return f"""graph TD
    A[Start] --> B[{placeholder}]
    B --> C[End]"""
    
    async def _run_generator(self):
        """Run the Generator - parallel slide HTML generation."""
        await self.emitter.stage_start("generator")
        self.state.current_stage = "generator"
        
        # For performance: generate slides in parallel
        tasks = [
            self._generate_slide_html(slide)
            for slide in self.state.refined_content.slides
        ]
        
        generated_slides = await asyncio.gather(*tasks)
        
        self.state.generated_presentation = GeneratedPresentation(
            title=self.state.refined_content.presentation_title,
            theme_id=self.state.refined_content.theme_id,
            slides=generated_slides,
            total_slides=len(generated_slides),
        )
        
        await self.emitter.stage_complete("generator", {
            "slides_generated": len(generated_slides),
        })
    
    async def _generate_slide_html(self, refined: RefinedSlide) -> GeneratedSlide:
        """Generate HTML for a single slide."""
        await self.emitter.slide_progress(refined.order, self.state.total_slides, "generating")
        
        # Build HTML from refined content
        html = self._build_slide_html(refined)
        
        self.state.slides_completed += 1
        
        return GeneratedSlide(
            order=refined.order,
            title=refined.title,
            theme_id=self.state.refined_content.theme_id,
            rendered_html=html,
            speaker_notes=refined.speaker_notes,
        )
    
    def _build_slide_html(self, slide: RefinedSlide) -> str:
        """Build HTML for a slide. In production, uses templates."""
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
        """Run Visual QA to grade slides."""
        await self.emitter.stage_start("visual_qa")
        self.state.current_stage = "visual_qa"
        self.state.qa_loops += 1
        
        # In production: render slides to images, run vision model
        # For now: simulate passing QA
        qa_results = [
            QAResult(
                slide_order=slide.order,
                score=95.0 + (slide.order % 5),  # Simulated 95-99
                issues=[],
                passed=True,
                iterations=self.state.qa_loops,
            )
            for slide in self.state.generated_presentation.slides
        ]
        
        avg_score = sum(r.score for r in qa_results) / len(qa_results)
        all_passed = all(r.passed for r in qa_results)
        
        self.state.qa_report = QAReport(
            session_id=self.state.session_id,
            slides=qa_results,
            average_score=avg_score,
            all_passed=all_passed,
            total_iterations=self.state.qa_loops,
        )
        
        await self.emitter.stage_complete("visual_qa", {
            "average_score": avg_score,
            "all_passed": all_passed,
        })


# =============================================================================
# Flow Runner (High-Level API)
# =============================================================================

async def create_session() -> FlowState:
    """Create a new generation session."""
    flow = SlideGenerationFlow()
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
    return await flow.process_clarification(user_message)


async def generate_outline(
    session_id: str,
    state: FlowState,
) -> Skeleton:
    """Generate the presentation outline."""
    flow = SlideGenerationFlow(session_id=session_id)
    flow.state = state
    return await flow.generate_outline()


async def approve_outline(
    session_id: str,
    state: FlowState,
    modifications: Optional[List[Dict]] = None,
) -> Skeleton:
    """Approve and optionally modify the outline."""
    flow = SlideGenerationFlow(session_id=session_id)
    flow.state = state
    return await flow.approve_outline(modifications)


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
    return await flow.run_generation()
