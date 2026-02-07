"""
Convex Service for Backend

Provides async methods for the Python backend to push updates to Convex.
Wraps the synchronous Convex client in async-friendly methods.
"""

import asyncio
import logging
from typing import Any, Optional
from app.core.convex_client import get_convex_client

logger = logging.getLogger(__name__)


class ConvexService:
    """
    Async service for interacting with Convex from the Python backend.
    
    All methods run the sync Convex client in a thread pool to avoid
    blocking the async event loop.
    """
    
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout
        self._client = None
    
    @property
    def client(self):
        if self._client is None:
            self._client = get_convex_client()
        return self._client
    
    async def _run_mutation(self, mutation_name: str, **kwargs) -> Any:
        """Run a Convex mutation asynchronously."""
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.mutation,
                    mutation_name,
                    kwargs
                ),
                timeout=self.timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"Convex mutation timeout: {mutation_name}")
            raise
        except Exception as e:
            logger.error(f"Convex mutation error ({mutation_name}): {e}")
            raise
    
    # =========================================================================
    # Generation Progress Methods
    # =========================================================================
    
    async def start_generation(self, project_id: str, session_id: str) -> str:
        """
        Start tracking a new generation session.
        
        Args:
            project_id: Convex project document ID
            session_id: Playground session UUID
            
        Returns:
            The generation progress document ID
        """
        return await self._run_mutation(
            "generation:startGeneration",
            projectId=project_id,
            sessionId=session_id,
        )
    
    async def update_progress(
        self,
        session_id: str,
        current_step: str,
        step_progress: int,
        current_slide_index: Optional[int] = None,
        total_slides: Optional[int] = None,
        message: Optional[str] = None,
    ) -> None:
        """
        Update generation progress.
        
        Args:
            session_id: Playground session UUID
            current_step: One of 'parsing', 'outlining', 'generating', 'rendering'
            step_progress: 0-100 percentage
            current_slide_index: Current slide being generated (0-indexed)
            total_slides: Total number of slides to generate
            message: Human-readable status message
        """
        kwargs: dict[str, Any] = {
            "sessionId": session_id,
            "currentStep": current_step,
            "stepProgress": step_progress,
        }
        if current_slide_index is not None:
            kwargs["currentSlideIndex"] = current_slide_index
        if total_slides is not None:
            kwargs["totalSlides"] = total_slides
        if message is not None:
            kwargs["message"] = message
            
        await self._run_mutation("generation:updateProgress", **kwargs)
    
    async def complete_generation(
        self,
        session_id: str,
        slides_data: Optional[Any] = None,
    ) -> None:
        """
        Mark generation as complete and save slides data.
        
        Args:
            session_id: Playground session UUID
            slides_data: Generated slides JSON data
        """
        kwargs: dict[str, Any] = {"sessionId": session_id}
        if slides_data is not None:
            kwargs["slidesData"] = slides_data
            
        await self._run_mutation("generation:completeGeneration", **kwargs)
    
    async def fail_generation(self, session_id: str, error: str) -> None:
        """
        Mark generation as failed.
        
        Args:
            session_id: Playground session UUID
            error: Error message to display
        """
        await self._run_mutation(
            "generation:failGeneration",
            sessionId=session_id,
            error=error,
        )
    
    # =========================================================================
    # Project Methods
    # =========================================================================
    
    async def update_project(
        self,
        project_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        slides_data: Optional[Any] = None,
    ) -> None:
        """Update a project's fields."""
        kwargs: dict[str, Any] = {"id": project_id}
        if title is not None:
            kwargs["title"] = title
        if description is not None:
            kwargs["description"] = description
        if status is not None:
            kwargs["status"] = status
        if slides_data is not None:
            kwargs["slidesData"] = slides_data
            
        await self._run_mutation("projects:update", **kwargs)

    async def save_outline(
        self,
        session_id: str,
        outline_data: Any,
    ) -> None:
        """
        Save the generated outline/blueprint to Convex.

        Args:
            session_id: Playground session UUID
            outline_data: Dictionary containing the skeleton/blueprint
        """
        await self._run_mutation(
            "generation:updateProgress",
            sessionId=session_id,
            currentStep="outlining",
            stepProgress=100,
            message="Blueprint ready for review",
            blueprint=outline_data,
            clarificationStatus="blueprint_ready"
        )


# Singleton instance
_convex_service: Optional[ConvexService] = None


def get_convex_service() -> ConvexService:
    """Get or create the Convex service singleton."""
    global _convex_service
    if _convex_service is None:
        _convex_service = ConvexService()
    return _convex_service
