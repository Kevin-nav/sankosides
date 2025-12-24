"""
Failure Report Service

Handles creation and storage of failure reports when the Helper
agent exhausts its retry budget.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import PlaygroundSession, FailureReport
from app.crew.agents.helper import FailureContext, HelperDecision
from app.core.logging import get_logger

logger = get_logger(__name__)


async def create_failure_report(
    session: AsyncSession,
    playground_session_id: UUID,
    failure_context: FailureContext,
    helper_attempts: List[Dict[str, Any]],
) -> FailureReport:
    """
    Create and store a failure report in the database.
    
    Called when the Helper agent exhausts its retry budget (2 attempts).
    
    Args:
        session: Database session
        playground_session_id: ID of the PlaygroundSession
        failure_context: Details about the failure
        helper_attempts: List of attempted fixes and their results
        
    Returns:
        The created FailureReport
    """
    report = FailureReport(
        session_id=playground_session_id,
        failing_agent=failure_context.failing_agent,
        failure_type=failure_context.failure_type,
        error_message=failure_context.error_message,
        agent_input=failure_context.agent_input,
        agent_output=failure_context.agent_output,
        helper_attempts=helper_attempts,
    )
    
    session.add(report)
    await session.commit()
    await session.refresh(report)
    
    logger.warning(
        f"Created failure report: id={report.id}, "
        f"agent={failure_context.failing_agent}, "
        f"type={failure_context.failure_type}"
    )
    
    return report


async def update_session_status(
    session: AsyncSession,
    session_id: UUID,
    status: str,
    current_stage: Optional[str] = None,
    qa_loops_count: Optional[int] = None,
    helper_retries: Optional[int] = None,
    final_qa_score: Optional[float] = None,
):
    """
    Update the status of a PlaygroundSession.
    
    Args:
        session: Database session
        session_id: ID of the PlaygroundSession
        status: New status (active, completed, failed)
        current_stage: Current pipeline stage
        qa_loops_count: Number of QA iterations
        helper_retries: Number of Helper interventions
        final_qa_score: Final QA score if completed
    """
    from sqlalchemy import select, update
    
    stmt = (
        update(PlaygroundSession)
        .where(PlaygroundSession.id == session_id)
        .values(
            status=status,
            updated_at=datetime.utcnow(),
            **({"current_stage": current_stage} if current_stage else {}),
            **({"qa_loops_count": qa_loops_count} if qa_loops_count is not None else {}),
            **({"helper_retries": helper_retries} if helper_retries is not None else {}),
            **({"final_qa_score": final_qa_score} if final_qa_score is not None else {}),
        )
    )
    
    await session.execute(stmt)
    await session.commit()
    
    logger.info(f"Updated session {session_id}: status={status}")


async def save_flow_state(
    session: AsyncSession,
    session_id: UUID,
    order_form: Optional[Dict] = None,
    skeleton: Optional[Dict] = None,
    planned_content: Optional[Dict] = None,
    refined_content: Optional[Dict] = None,
    generated_slides: Optional[Dict] = None,
):
    """
    Save the current flow state to the database.
    
    Called after each major stage to persist progress.
    
    Args:
        session: Database session
        session_id: ID of the PlaygroundSession
        order_form: Clarifier output
        skeleton: Outliner output
        planned_content: Planner output
        refined_content: Refiner output
        generated_slides: Generator output
    """
    from sqlalchemy import update
    
    values = {"updated_at": datetime.utcnow()}
    
    if order_form is not None:
        values["order_form"] = order_form
    if skeleton is not None:
        values["skeleton"] = skeleton
    if planned_content is not None:
        values["planned_content"] = planned_content
    if refined_content is not None:
        values["refined_content"] = refined_content
    if generated_slides is not None:
        values["generated_slides"] = generated_slides
    
    stmt = (
        update(PlaygroundSession)
        .where(PlaygroundSession.id == session_id)
        .values(**values)
    )
    
    await session.execute(stmt)
    await session.commit()
    
    logger.info(f"Saved flow state for session {session_id}")


async def get_failure_reports(
    session: AsyncSession,
    limit: int = 100,
    failing_agent: Optional[str] = None,
) -> List[FailureReport]:
    """
    Retrieve failure reports for admin review.
    
    Args:
        session: Database session
        limit: Maximum number of reports to return
        failing_agent: Optional filter by agent name
        
    Returns:
        List of FailureReport objects
    """
    from sqlalchemy import select
    
    stmt = select(FailureReport).order_by(FailureReport.created_at.desc()).limit(limit)
    
    if failing_agent:
        stmt = stmt.where(FailureReport.failing_agent == failing_agent)
    
    result = await session.execute(stmt)
    return list(result.scalars().all())
