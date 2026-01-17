"""
Render Worker - Background Thread with Connection Pooling

Provides a dedicated thread with persistent event loop for render service calls.
This avoids "Event loop is closed" errors when calling async HTTP from sync contexts.

Usage:
    worker = RenderWorker.get_instance()
    result = worker.render_latex_sync("E = mc^2")
"""

import asyncio
import threading
import httpx
from typing import Optional, Dict, Any
from queue import Queue
from concurrent.futures import Future

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default render service URL from settings
RENDER_SERVICE_URL = settings.render_service_url


class RenderWorker:
    """
    Singleton background worker with dedicated event loop.
    
    Uses a persistent httpx.AsyncClient for connection pooling,
    avoiding the overhead of creating new connections per request.
    """
    
    _instance: Optional["RenderWorker"] = None
    _lock = threading.Lock()
    
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._client: Optional[httpx.AsyncClient] = None
        self._queue: Queue = Queue()
        self._running = False
        self._ready = threading.Event()
        self.base_url = RENDER_SERVICE_URL
    
    @classmethod
    def get_instance(cls) -> "RenderWorker":
        """Get or create the singleton worker instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = RenderWorker()
                    cls._instance.start()
        return cls._instance
    
    def start(self):
        """Start the background worker thread."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="RenderWorker")
        self._thread.start()
        
        # Wait for loop to be ready
        self._ready.wait(timeout=5.0)
        logger.info("RenderWorker started with connection pooling")
    
    def _run_loop(self):
        """Run the event loop in the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # Create persistent client with connection pooling
        self._client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5)
        )
        
        # Signal ready
        self._ready.set()
        
        # Process queue
        while self._running:
            try:
                task = self._queue.get(timeout=0.5)
                if task is None:
                    break
                
                future, coro = task
                try:
                    result = self._loop.run_until_complete(coro)
                    future.set_result(result)
                except Exception as e:
                    future.set_exception(e)
            except Exception:
                # Queue timeout, continue
                pass
        
        # Cleanup
        if self._client:
            self._loop.run_until_complete(self._client.aclose())
        self._loop.close()
        logger.info("RenderWorker stopped")
    
    def stop(self):
        """Stop the background worker."""
        self._running = False
        self._queue.put(None)
        if self._thread:
            self._thread.join(timeout=5.0)
    
    def _submit(self, coro) -> Future:
        """Submit a coroutine to the background worker."""
        future = Future()
        self._queue.put((future, coro))
        return future
    
    # =========================================================================
    # Async Methods (run in background thread)
    # =========================================================================
    
    async def _render_latex_async(self, latex: str, display: bool = True) -> Dict[str, Any]:
        """Render LaTeX to SVG."""
        try:
            response = await self._client.post(
                f"{self.base_url}/render/latex",
                json={"latex": latex, "display": display}
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _render_mermaid_async(self, diagram: str) -> Dict[str, Any]:
        """Render Mermaid diagram to SVG."""
        try:
            response = await self._client.post(
                f"{self.base_url}/render/mermaid",
                json={"diagram": diagram}
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _format_citation_async(
        self, 
        citations: list, 
        style: str = "apa"
    ) -> Dict[str, Any]:
        """Format citations."""
        try:
            response = await self._client.post(
                f"{self.base_url}/render/citation",
                json={"citations": citations, "style": style}
            )
            return response.json()
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # =========================================================================
    # Sync Methods (for use from any context)
    # =========================================================================
    
    def render_latex_sync(self, latex: str, display: bool = True, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Render LaTeX synchronously from any thread/context.
        
        Args:
            latex: LaTeX string to render
            display: Whether to use display mode
            timeout: Maximum wait time in seconds
            
        Returns:
            Dict with 'svg' on success, 'error' on failure
        """
        future = self._submit(self._render_latex_async(latex, display))
        return future.result(timeout=timeout)
    
    def render_mermaid_sync(self, diagram: str, timeout: float = 30.0) -> Dict[str, Any]:
        """
        Render Mermaid diagram synchronously from any thread/context.
        
        Args:
            diagram: Mermaid diagram code
            timeout: Maximum wait time in seconds
            
        Returns:
            Dict with 'svg' on success, 'error' on failure
        """
        future = self._submit(self._render_mermaid_async(diagram))
        return future.result(timeout=timeout)
    
    def format_citation_sync(
        self, 
        citations: list, 
        style: str = "apa",
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Format citations synchronously from any thread/context.
        
        Args:
            citations: List of citation dicts
            style: Citation style (apa, ieee, harvard, chicago)
            timeout: Maximum wait time in seconds
            
        Returns:
            Dict with 'citations' array on success
        """
        future = self._submit(self._format_citation_async(citations, style))
        return future.result(timeout=timeout)


# Convenience function
def get_render_worker() -> RenderWorker:
    """Get the singleton RenderWorker instance."""
    return RenderWorker.get_instance()
