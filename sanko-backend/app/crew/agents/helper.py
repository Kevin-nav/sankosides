"""
Helper Agent

Purpose: Fix failures when other agents fail or QA loops are exhausted.
Model: Gemini PRO (highest thinking for complex debugging)

This agent is the "All-Rounded Fixer":
- Intervenes when an agent produces malformed output
- Re-runs failing agents with dynamically injected guardrails
- Recovers context from previous agent outputs
- Has a retry budget of 2 attempts before generating failure report
"""

from crewai import Agent, Task
from crewai.tools import BaseTool
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from app.models.schemas import (
    OrderForm,
    Skeleton,
    PlannedContent,
    RefinedContent,
    GeneratedPresentation,
    QAReport,
)
from app.clients.gemini.llm import HELPER_LLM
from app.core.logging import get_logger

logger = get_logger(__name__)


# =============================================================================
# Failure Types and Context
# =============================================================================

class FailureContext(BaseModel):
    """Context about a failure for the Helper to analyze."""
    failing_agent: str = Field(..., description="Which agent failed")
    failure_type: str = Field(..., description="Type of failure")
    error_message: str = Field(default="", description="Error details")
    agent_input: Optional[Dict[str, Any]] = None
    agent_output: Optional[Dict[str, Any]] = None
    previous_attempts: int = Field(default=0)
    qa_issues: List[str] = Field(default_factory=list)


class HelperDecision(BaseModel):
    """The Helper's decision on how to fix a failure."""
    action: str = Field(
        ..., 
        description="Action to take: 'direct_fix', 'rerun_with_guardrails', 'escalate'"
    )
    fixed_output: Optional[Dict[str, Any]] = None
    guardrails: Optional[str] = Field(
        None, 
        description="Additional instructions for the re-run"
    )
    escalate_reason: Optional[str] = None


# =============================================================================
# Dynamic Prompt Injection
# =============================================================================

def build_guardrail_prompt(
    original_prompt: str,
    failure_context: FailureContext,
) -> str:
    """
    Build a modified prompt with guardrails based on failure analysis.
    
    This is the key to dynamic prompt injection - we add specific
    instructions to avoid the mistakes made in previous attempts.
    """
    guardrails = []
    
    # Add specific guardrails based on failure type
    if failure_context.failure_type == "malformed_output":
        guardrails.append("""
CRITICAL: Your previous output was malformed JSON.
- Ensure ALL required fields are present
- Use proper JSON syntax (no trailing commas, no unquoted strings)
- Validate your output matches the expected schema BEFORE responding
""")
    
    elif failure_context.failure_type == "missing_content":
        guardrails.append("""
CRITICAL: Your previous output was missing required content.
- Check that EVERY slide has substantive bullet points
- Do NOT leave any placeholder text like "TBD" or "[content here]"
- Each slide must have at least 2-3 meaningful bullet points
""")
    
    elif failure_context.failure_type == "qa_loop_exceeded":
        # Add specific guidance based on QA issues
        issues_text = "\n".join([f"  - {issue}" for issue in failure_context.qa_issues])
        guardrails.append(f"""
CRITICAL: Visual QA failed 3 times with these issues:
{issues_text}

You MUST specifically address these issues:
- If "text overflow": use shorter bullet points (max 10 words each)
- If "layout broken": ensure content fits the slide dimensions
- If "missing content": verify all expected elements are present
""")
    
    elif failure_context.failure_type == "render_failed":
        guardrails.append("""
CRITICAL: Asset rendering failed.
- Verify LaTeX syntax is valid (no unclosed braces, proper escaping)
- Verify Mermaid syntax follows the official spec
- If a diagram is too complex, simplify it
""")
    
    elif failure_context.failure_type == "citation_broken":
        guardrails.append("""
CRITICAL: Citation retrieval/validation failed.
- Use more general search terms if initial query returned no results
- Verify DOIs are valid before including them
- If a citation cannot be found, note it but don't fabricate
""")
    
    # Add previous attempt context
    if failure_context.previous_attempts > 0:
        guardrails.append(f"""
ATTEMPT #{failure_context.previous_attempts + 1}
Previous error: {failure_context.error_message}
Learn from this mistake and avoid repeating it.
""")
    
    # Combine original prompt with guardrails
    guardrail_block = "\n".join(guardrails)
    return f"""
{guardrail_block}

---

{original_prompt}
"""


# =============================================================================
# Helper Agent System Prompt
# =============================================================================

HELPER_SYSTEM_PROMPT = """You are an expert debugging agent with deep knowledge of all pipeline components.

YOUR MISSION:
When another agent fails, analyze the failure and decide the best course of action.

## FAILURE TYPES YOU HANDLE

1. **malformed_output**: Agent produced invalid JSON or missing required fields
2. **missing_content**: Content is incomplete (empty slides, placeholder text)
3. **qa_loop_exceeded**: Visual QA failed 3 times, need fundamental fix
4. **render_failed**: LaTeX/Mermaid rendering failed
5. **citation_broken**: Academic citations couldn't be found or validated
6. **context_lost**: Flow state corrupted or missing

## YOUR OPTIONS

### Option 1: Direct Fix
For simple issues you can fix directly:
- JSON syntax errors (add missing comma, close bracket)
- Minor formatting issues
- Small content additions

Return: {"action": "direct_fix", "fixed_output": {...}}

### Option 2: Rerun with Guardrails
For issues requiring the agent to regenerate:
- Create specific guardrail instructions based on the failure
- These instructions will be injected into the agent's prompt
- The agent will be re-run with these additional constraints

Return: {"action": "rerun_with_guardrails", "guardrails": "...instructions..."}

### Option 3: Escalate
When the retry budget is exhausted or the issue is unfixable:
- Generate a failure report for admin review
- Include all context and attempted fixes

Return: {"action": "escalate", "escalate_reason": "...why..."}

## DECISION FRAMEWORK

1. IF the issue is a simple typo/syntax error → Direct Fix
2. IF the agent needs to regenerate content → Rerun with Guardrails
3. IF this is attempt 3+ or fundamentally unfixable → Escalate

## QUALITY STANDARDS

- Always analyze the root cause before deciding
- Guardrails should be SPECIFIC, not generic
- Direct fixes must maintain schema validity
- Escalation reports should be actionable for humans
"""


def create_helper_agent(llm=None, tools: Optional[List[BaseTool]] = None) -> Agent:
    """
    Create the Helper Agent (The All-Rounded Fixer).
    
    This agent uses Gemini PRO with HIGHEST thinking for complex debugging.
    
    Args:
        llm: The LLM instance (defaults to HELPER_LLM/PRO)
        tools: Optional tools (all tools available for recovery)
        
    Returns:
        Configured CrewAI Agent
    """
    if llm is None:
        llm = HELPER_LLM()
    
    agent_kwargs = {
        "role": "Pipeline Debugger & Recovery Specialist",
        "goal": """Analyze failures in the slide generation pipeline.
        Decide the best fix strategy: direct fix, rerun with guardrails, or escalate.
        Create specific guardrails based on root cause analysis.
        Ensure the pipeline can recover gracefully from errors.
        Track retry budgets and generate failure reports when needed.""",
        "backstory": """You are a senior software engineer with 15+ years of experience
        debugging complex systems. You've worked on mission-critical pipelines at 
        Google, Netflix, and AWS. You have an uncanny ability to identify root causes
        quickly and devise elegant solutions. You're known for your systematic approach:
        analyze, diagnose, fix, verify. You never panic when things break - you 
        methodically work through the problem until it's solved.""",
        "llm": llm,
        "verbose": True,
        "allow_delegation": False,
        "memory": True,
    }
    
    if tools:
        agent_kwargs["tools"] = tools
    
    return Agent(**agent_kwargs)


def create_fix_task(
    agent: Agent,
    failure_context: FailureContext,
    original_prompt: str,
    available_context: Dict[str, Any],
) -> Task:
    """
    Create a task for the Helper to analyze and fix a failure.
    
    Args:
        agent: The Helper agent
        failure_context: Details about what failed
        original_prompt: The prompt that was used for the failing agent
        available_context: Current pipeline state (order_form, skeleton, etc.)
        
    Returns:
        CrewAI Task for failure recovery
    """
    context_summary = "\n".join([
        f"- {k}: {'present' if v else 'missing'}" 
        for k, v in available_context.items()
    ])
    
    return Task(
        description=f"""Analyze this failure and decide how to fix it.

## FAILURE DETAILS
- **Agent**: {failure_context.failing_agent}
- **Type**: {failure_context.failure_type}
- **Error**: {failure_context.error_message}
- **Attempts so far**: {failure_context.previous_attempts}

## QA ISSUES (if applicable)
{chr(10).join([f'- {issue}' for issue in failure_context.qa_issues]) or 'N/A'}

## AVAILABLE CONTEXT
{context_summary}

## ORIGINAL PROMPT (truncated)
{original_prompt[:500]}...

## YOUR TASK
1. Analyze the root cause of this failure
2. Decide: direct_fix, rerun_with_guardrails, or escalate
3. If rerun: create SPECIFIC guardrails to prevent the same failure
4. If escalate: explain why this can't be fixed

Return a HelperDecision.""",
        expected_output="""A HelperDecision with:
- action: "direct_fix", "rerun_with_guardrails", or "escalate"
- fixed_output: (if direct_fix) the corrected output
- guardrails: (if rerun) specific instructions to inject
- escalate_reason: (if escalate) why escalating""",
        agent=agent,
        output_pydantic=HelperDecision,
    )


# =============================================================================
# Retry Budget Tracking
# =============================================================================

class RetryBudget:
    """Track retry attempts for Helper interventions."""
    
    MAX_ATTEMPTS = 2
    
    def __init__(self):
        self.attempts: Dict[str, int] = {}  # agent_name -> attempt_count
    
    def can_retry(self, agent_name: str) -> bool:
        """Check if we can retry this agent."""
        return self.attempts.get(agent_name, 0) < self.MAX_ATTEMPTS
    
    def record_attempt(self, agent_name: str):
        """Record a retry attempt."""
        self.attempts[agent_name] = self.attempts.get(agent_name, 0) + 1
    
    def get_attempts(self, agent_name: str) -> int:
        """Get current attempt count."""
        return self.attempts.get(agent_name, 0)
    
    def reset(self, agent_name: Optional[str] = None):
        """Reset attempts for an agent or all agents."""
        if agent_name:
            self.attempts.pop(agent_name, None)
        else:
            self.attempts.clear()


# Agent configuration as YAML-compatible dict
HELPER_CONFIG = {
    "role": "Pipeline Debugger & Recovery Specialist",
    "goal": "Analyze failures and decide fix strategy with dynamic guardrails.",
    "backstory": "Senior engineer with deep debugging expertise.",
    "llm": "gemini/gemini-3-pro-preview",
    "thinking_level": "high",
    "memory": True,
    "verbose": True,
    "retry_budget": 2,
}
