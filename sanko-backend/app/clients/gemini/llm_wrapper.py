"""
CrewAI-Compatible LLM Wrapper for Gemini Interactions API

This class can be used with CrewAI agents while maintaining
stateful conversations via the Interactions API.

Usage:
    llm = GeminiInteractionsLLM(api_key="...", model="gemini-3-flash-preview")
    agent = Agent(llm=llm, ...)
"""

import asyncio
from typing import Optional, List, Dict

from app.logging_config import get_logger

logger = get_logger(__name__)


class GeminiInteractionsLLM:
    """
    CrewAI-compatible LLM wrapper for Gemini Interactions API.
    
    This class can be used with CrewAI agents while maintaining
    stateful conversations via the Interactions API.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3-flash-preview",
        thinking_level: str = "low",
    ):
        # Lazy import to avoid circular dependency
        from app.services.gemini.client import GeminiInteractionsClient
        
        self.api_key = api_key
        self.model = model
        self.thinking_level = thinking_level
        self.client = GeminiInteractionsClient(api_key)
        self.interaction_id: Optional[str] = None
        self.supports_system_prompt = True
    
    def call(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Synchronous call method for CrewAI compatibility.
        
        Note: This wraps the async client for sync usage.
        
        Args:
            messages: List of message dicts with role and content
            
        Returns:
            Response text from the model
        """
        # Extract the latest message
        if isinstance(messages, list) and messages:
            prompt = messages[-1].get("content", "")
        else:
            prompt = str(messages)
        
        # Run async call in event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If already in async context, use thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    self._async_call(prompt)
                )
                return future.result()
        else:
            return loop.run_until_complete(self._async_call(prompt))
    
    async def _async_call(self, prompt: str) -> str:
        """Internal async call."""
        if self.interaction_id:
            result = await self.client.continue_interaction(
                interaction_id=self.interaction_id,
                prompt=prompt,
                model=self.model,
            )
        else:
            result = await self.client.create_interaction(
                prompt=prompt,
                model=self.model,
            )
        
        self.interaction_id = result.get("interaction_id")
        return result.get("response", "")
    
    def reset_session(self):
        """Reset the interaction session (start fresh)."""
        self.interaction_id = None
        logger.info("LLM session reset")
