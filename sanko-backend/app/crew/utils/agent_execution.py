"""
Agent Execution Utility

Provides robust wrapper for executing CrewAI agents with:
- Configurable timeouts via environment variables
- Retry logic with exponential backoff for transient errors
- Circuit breaker pattern to prevent cascading failures
- Structured logging for monitoring

Usage:
    from app.crew.utils.agent_execution import execute_crew_with_retry
    
    result = await execute_crew_with_retry(crew, "outliner")
"""

import asyncio
import time
from typing import Any, Optional, Dict
from datetime import datetime, timedelta

from crewai import Crew

from app.core.logging import get_logger
from app.core.config import settings
from app.clients.gemini.retry import is_retryable_gemini_error, extract_retry_after

logger = get_logger(__name__)


# ===========================================================================
# Circuit Breaker State (prevent cascading failures)
# ===========================================================================

class CircuitBreaker:
    """
    Circuit breaker to prevent cascading failures when the AI service is overloaded.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service is failing, reject requests immediately
    - HALF_OPEN: Testing if service has recovered
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        name: str = "default"
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout  # seconds
        self.name = name
        
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"
    
    def record_success(self):
        """Record a successful execution."""
        self.failure_count = 0
        self.state = "CLOSED"
        logger.debug(f"[CIRCUIT:{self.name}] Success recorded, state: CLOSED")
    
    def record_failure(self):
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"[CIRCUIT:{self.name}] Circuit OPEN after {self.failure_count} failures. "
                f"Will recover after {self.recovery_timeout}s"
            )
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == "CLOSED":
            return True
        
        if self.state == "OPEN":
            # Check if recovery timeout has passed
            if self.last_failure_time:
                time_since_failure = (datetime.now() - self.last_failure_time).total_seconds()
                if time_since_failure >= self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    logger.info(f"[CIRCUIT:{self.name}] Moving to HALF_OPEN state for testing")
                    return True
            return False
        
        # HALF_OPEN: allow one request through to test
        return True


# Global circuit breakers per stage
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(stage_name: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a stage."""
    if stage_name not in _circuit_breakers:
        _circuit_breakers[stage_name] = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            name=stage_name
        )
    return _circuit_breakers[stage_name]


# ===========================================================================
# Timeout Configuration
# ===========================================================================

def get_timeout_for_stage(stage_name: str) -> int:
    """Get the configured timeout for a stage."""
    timeout_map = {
        "clarifier": settings.agent_timeout_outliner,
        "outliner": settings.agent_timeout_outliner,
        "planner": settings.agent_timeout_planner,
        "refiner": settings.agent_timeout_refiner,
        "generator": settings.agent_timeout_generator,
        "visual_qa": settings.agent_timeout_visual_qa,
        "helper": settings.agent_timeout_refiner,
    }
    return timeout_map.get(stage_name, 180)  # Default 180s


# ===========================================================================
# Main Execution Wrapper
# ===========================================================================

async def execute_crew_with_retry(
    crew: Crew,
    stage_name: str,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None,
    session_id: Optional[str] = None,
) -> Any:
    """
    Execute a CrewAI crew with timeout, retries, and circuit breaker.
    
    Args:
        crew: The CrewAI Crew instance to execute
        stage_name: Name of the stage (for logging and config lookup)
        timeout: Override timeout in seconds (default: from config)
        max_retries: Override max retries (default: from config)
    
    Returns:
        The result from crew.kickoff()
    
    Raises:
        RuntimeError: If the circuit breaker is open or all retries exhausted
    """
    # Get configuration
    stage_timeout = timeout or get_timeout_for_stage(stage_name)
    retries = max_retries if max_retries is not None else settings.agent_max_retries
    
    # Check circuit breaker
    circuit = get_circuit_breaker(stage_name)
    if not circuit.can_execute():
        logger.error(f"[{stage_name.upper()}] Circuit breaker OPEN - rejecting request")
        raise RuntimeError(
            f"The {stage_name} service is temporarily unavailable due to high error rate. "
            f"Please try again in {circuit.recovery_timeout} seconds."
        )
    
    last_exception = None
    
    for attempt in range(1, retries + 1):
        try:
            logger.info(
                f"[{stage_name.upper()}] Executing (attempt {attempt}/{retries}, "
                f"timeout: {stage_timeout}s)"
            )
            
            start_time = time.time()
            
            # Execute in thread pool with timeout
            loop = asyncio.get_running_loop()
            result = await asyncio.wait_for(
                loop.run_in_executor(None, crew.kickoff),
                timeout=stage_timeout
            )
            
            elapsed = time.time() - start_time
            logger.info(f"[{stage_name.upper()}] Completed successfully in {elapsed:.1f}s")

            # Record token usage + timings (best-effort).
            if session_id:
                try:
                    from app.crew.flows.metrics import MetricsCollector, extract_usage_from_response
                    from app.core.posthog import capture as posthog_capture, build_common_props

                    model_name = ""
                    try:
                        if getattr(crew, "agents", None):
                            agent0 = crew.agents[0]
                            llm = getattr(agent0, "llm", None)
                            model_name = getattr(llm, "model", "") or ""
                    except Exception:
                        model_name = ""

                    usage = extract_usage_from_response(result, model=model_name)
                    duration_ms = int(elapsed * 1000)
                    collector = MetricsCollector.get_or_create(session_id)
                    collector.record(
                        stage_name,
                        usage,
                        duration_ms=duration_ms,
                    )

                    # High ROI: per-agent-per-run event for cost attribution in PostHog.
                    # This enables: cost per session, per user, per project, per agent, per run.
                    try:
                        ctx = collector.get_context() if hasattr(collector, "get_context") else {}
                        user_id = ctx.get("user_id") if isinstance(ctx, dict) else None
                        project_id = ctx.get("project_id") if isinstance(ctx, dict) else None
                        mode = ctx.get("mode") if isinstance(ctx, dict) else None

                        distinct_id = (
                            str(user_id).strip()
                            if isinstance(user_id, str) and user_id.strip()
                            else (
                                str(project_id).strip()
                                if isinstance(project_id, str) and project_id.strip()
                                else session_id
                            )
                        )

                        cost_usd = 0.0
                        try:
                            cost_usd = float(usage.calculate_cost() or 0.0)
                        except Exception:
                            cost_usd = 0.0

                        props = build_common_props(
                            session_id=session_id,
                            project_id=str(project_id) if project_id else None,
                            user_id=str(user_id) if user_id else None,
                            mode=mode or None,
                            agent_name=stage_name,
                            model=(model_name or None),
                            duration_ms=duration_ms,
                            input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
                            output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
                            thinking_tokens=int(getattr(usage, "thinking_tokens", 0) or 0),
                            total_tokens=int(getattr(usage, "total_tokens", 0) or 0),
                            cost_usd=cost_usd,
                            success=True,
                            attempt=int(attempt),
                            **({"$groups": {"project": str(project_id)}} if project_id else {}),
                        )
                        posthog_capture(event="agent_run_metrics", distinct_id=distinct_id, properties=props)
                    except Exception:
                        pass
                except Exception:
                    pass
            
            # Record success
            circuit.record_success()
            
            return result
            
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            logger.warning(
                f"[{stage_name.upper()}] Timed out after {elapsed:.1f}s "
                f"(attempt {attempt}/{retries})"
            )
            last_exception = TimeoutError(
                f"{stage_name.capitalize()} agent timed out after {stage_timeout}s"
            )
            circuit.record_failure()
            
            # Don't retry timeouts - they're usually not transient
            if attempt == retries:
                break
            
            # Wait a bit before retrying
            wait_time = min(5 * attempt, 15)  # 5s, 10s, 15s
            logger.info(f"[{stage_name.upper()}] Waiting {wait_time}s before retry...")
            await asyncio.sleep(wait_time)
            
        except Exception as e:
            elapsed = time.time() - start_time
            last_exception = e
            
            # Check if error is retryable
            if not is_retryable_gemini_error(e):
                logger.error(
                    f"[{stage_name.upper()}] Non-retryable error after {elapsed:.1f}s: {e}"
                )
                circuit.record_failure()
                raise
            
            logger.warning(
                f"[{stage_name.upper()}] Retryable error after {elapsed:.1f}s "
                f"(attempt {attempt}/{retries}): {e}"
            )
            circuit.record_failure()
            
            if attempt == retries:
                break
            
            # Calculate wait time with exponential backoff
            base_wait = min(2 ** (attempt - 1), 30)  # 1s, 2s, 4s, ..., max 30s
            
            # Check for API-suggested retry time
            suggested_wait = extract_retry_after(e)
            if suggested_wait > 0:
                base_wait = max(base_wait, suggested_wait)
            
            logger.info(
                f"[{stage_name.upper()}] Waiting {base_wait}s before retry..."
            )
            await asyncio.sleep(base_wait)
    
    # All retries exhausted
    logger.error(
        f"[{stage_name.upper()}] Failed after {retries} attempts. "
        f"Last error: {last_exception}"
    )
    
    raise RuntimeError(
        f"{stage_name.capitalize()} agent failed after {retries} attempts. "
        f"The AI service may be overloaded. Please try again later."
    ) from last_exception


# ===========================================================================
# Utility Functions
# ===========================================================================

def reset_circuit_breakers():
    """Reset all circuit breakers (for testing)."""
    for breaker in _circuit_breakers.values():
        breaker.failure_count = 0
        breaker.state = "CLOSED"
        breaker.last_failure_time = None
    logger.info("All circuit breakers reset")


def get_circuit_breaker_status() -> Dict[str, Any]:
    """Get status of all circuit breakers (for monitoring)."""
    return {
        name: {
            "state": breaker.state,
            "failure_count": breaker.failure_count,
            "last_failure": breaker.last_failure_time.isoformat() if breaker.last_failure_time else None,
        }
        for name, breaker in _circuit_breakers.items()
    }
