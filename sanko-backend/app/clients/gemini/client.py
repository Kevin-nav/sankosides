"""
Google Gemini Interactions API Client

Stateful client for the Gemini Interactions API.
Uses the google-genai SDK for proper server-side state management.

Key Features:
- Server-side state management (store=True)
- Multi-turn conversations via previous_interaction_id chaining
- Support for Deep Research agent (async background tasks)
- Native PDF/image processing via multimodal input
- Thinking level configuration for reasoning control
"""

from typing import Optional, Dict, Any, List, Union
import asyncio
import base64
import uuid
import json
from pathlib import Path

from google import genai
from google.genai import types

from app.core.logging import get_logger
from app.clients.gemini.helpers import (
    extract_token_usage,
    build_part,
    extract_thinking_from_response,
    extract_text_from_response,
)

logger = get_logger(__name__)


class GeminiInteractionsClient:
    """
    Stateful client for Google Gemini Interactions API.
    
    This client manages interaction_id to maintain server-side conversation state,
    dramatically reducing token usage for multi-turn conversations.
    """
    
    def __init__(self, api_key: str):
        """
        Initialize the Gemini Interactions client.
        
        Args:
            api_key: Google Gemini API key
        """
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
    
    def _extract_token_usage(self, response) -> Dict[str, int]:
        """Extract token usage from API response."""
        return extract_token_usage(response)
    
    async def create_interaction(
        self,
        prompt: Union[str, List[Dict]],
        model: str = "gemini-3-flash-preview",
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        store: bool = True,
        previous_interaction_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a stateful interaction using the Interactions API.
        
        USE THIS FOR: Multi-turn conversations where you need session state
                      (e.g., clarification flow with user).
        
        NOTE: The beta Interactions API does NOT support thinking_config.
              For thinking-enabled calls, use generate_with_thinking() instead.
        
        Args:
            prompt: The user's message (string or multimodal parts)
            model: Which Gemini model to use
            system_instruction: Optional system prompt
            tools: Optional list of tool definitions
            store: Whether to persist state server-side (default True)
            previous_interaction_id: For continuing a stateful session
            
        Returns:
            Dict containing:
            - interaction_id: Real session ID for subsequent turns
            - response: The model's response text
            - status: The interaction status
            - tokens: Token usage breakdown
        """
        try:
            loop = asyncio.get_event_loop()
            
            create_kwargs = {
                "model": model,
                "input": prompt,
                "store": store,
            }
            
            if system_instruction:
                create_kwargs["system_instruction"] = system_instruction
            
            if tools:
                create_kwargs["tools"] = tools
            
            if previous_interaction_id:
                create_kwargs["previous_interaction_id"] = previous_interaction_id
            
            interaction = await loop.run_in_executor(
                None,
                lambda: self.client.interactions.create(**create_kwargs)
            )
            
            # Extract response text from outputs
            response_text = ""
            if hasattr(interaction, 'outputs') and interaction.outputs:
                for output in interaction.outputs:
                    if hasattr(output, 'text') and output.text:
                        response_text += output.text
                    if hasattr(output, 'parts'):
                        for part in output.parts:
                            if hasattr(part, 'text') and part.text:
                                response_text += part.text
            
            token_usage = self._extract_token_usage(interaction)
            interaction_id = getattr(interaction, 'id', None) or getattr(interaction, 'name', '')
            
            return {
                "interaction_id": interaction_id,
                "response": response_text,
                "thinking": "",
                "status": getattr(interaction, 'status', 'completed'),
                "tokens": token_usage,
                "raw": interaction,
            }
            
        except Exception as e:
            logger.error(f"Failed to create interaction: {e}")
            raise Exception(f"Failed to create interaction: {str(e)}")
    
    async def continue_interaction(
        self,
        interaction_id: str,
        prompt: Union[str, List[Dict]],
        model: str = "gemini-3-flash-preview",
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Continue an existing interaction with a new message.
        
        Uses previous_interaction_id for stateful continuation.
        """
        return await self.create_interaction(
            prompt=prompt,
            model=model,
            system_instruction=system_instruction,
            tools=tools,
            previous_interaction_id=interaction_id,
        )
    
    async def generate_with_thinking(
        self,
        prompt: Union[str, List[Dict]],
        model: str = "gemini-3-flash-preview",
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        thinking_level: str = "high",
    ) -> Dict[str, Any]:
        """
        Generate content with thinking/reasoning mode enabled.
        
        USE THIS FOR: Complex reasoning tasks like planning, analysis, coding.
        
        NOTE: Uses models.generate_content (stateless) because the beta
              Interactions API does NOT support thinking_config.
        
        Args:
            prompt: The prompt (string or multimodal parts)
            model: Which Gemini model to use
            system_instruction: Optional system prompt
            tools: Optional list of tool definitions
            thinking_level: "minimal", "low", "medium", "high"
            
        Returns:
            Dict with response, thinking, and token usage
        """
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=thinking_level
            )
        )
        
        if system_instruction:
            config.system_instruction = system_instruction
        
        if tools:
            config.tools = tools
        
        try:
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
            )
            
            response_text = extract_text_from_response(response)
            thinking_text = extract_thinking_from_response(response)
            token_usage = self._extract_token_usage(response)
            
            return {
                "interaction_id": str(uuid.uuid4()),
                "response": response_text,
                "thinking": thinking_text,
                "status": "completed",
                "tokens": token_usage,
                "raw": response,
            }
            
        except Exception as e:
            logger.error(f"Failed to generate with thinking: {e}")
            raise Exception(f"Failed to generate with thinking: {str(e)}")
    
    async def generate_chat_with_thinking(
        self,
        history: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        model: str = "gemini-3-flash-preview",
        thinking_level: str = "low",
    ) -> Dict[str, Any]:
        """
        Generate with thinking using client-side history management.
        
        USE THIS FOR: Multi-turn conversations needing both history and thinking.
        """
        contents = []
        for msg in history:
            role = msg.get("role", "user")
            if role in ["assistant", "model"]:
                role = "model"
            elif role == "system":
                continue
            
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg.get("content", ""))]
            ))
        
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=thinking_level
            )
        )
        
        if system_instruction:
            config.system_instruction = system_instruction
        
        try:
            loop = asyncio.get_event_loop()
            
            response = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=config,
                )
            )
            
            response_text = extract_text_from_response(response)
            thinking_text = extract_thinking_from_response(response)
            token_usage = self._extract_token_usage(response)
            
            return {
                "interaction_id": str(uuid.uuid4()),
                "response": response_text,
                "thinking": thinking_text,
                "status": "completed",
                "tokens": token_usage,
                "raw": response,
            }
            
        except Exception as e:
            logger.error(f"Failed to generate chat with thinking: {e}")
            raise Exception(f"Failed to generate chat with thinking: {str(e)}")

    async def generate_with_thinking_stream(
        self,
        prompt: Union[str, List[Dict]],
        model: str = "gemini-3-flash-preview",
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict]] = None,
        thinking_level: str = "high",
    ):
        """
        Generate content with thinking mode enabled, yielding chunks.
        
        Uses a queue-based approach to properly yield chunks from sync stream.
        
        Yields:
            Dict with one of:
            - {"type": "thinking", "text": "..."}  - Thinking chunk
            - {"type": "content", "text": "..."}   - Content chunk
            - {"type": "done", "tokens": {...}}    - Final token counts
        """
        import queue
        import threading
        
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=thinking_level
            )
        )
        
        if system_instruction:
            config.system_instruction = system_instruction
            
        if tools:
            config.tools = tools
        
        # Thread-safe queue for passing chunks from sync to async
        chunk_queue = queue.Queue()
        error_holder = [None]
        
        # Track token usage - extracted from final chunk
        token_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "thinking_tokens": 0,
            "cached_tokens": 0,
            "total_tokens": 0,
        }
        
        def stream_in_thread():
            """Run the sync stream in a thread, pushing chunks to queue."""
            chunk_count = 0
            try:
                stream = self.client.models.generate_content_stream(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                
                for chunk in stream:
                    chunk_count += 1
                    if hasattr(chunk, 'candidates') and chunk.candidates:
                        for candidate in chunk.candidates:
                            if hasattr(candidate, 'content') and candidate.content:
                                for part in candidate.content.parts:
                                    # Debug: Log all part attributes to find thinking
                                    if chunk_count <= 3:
                                        part_attrs = [a for a in dir(part) if not a.startswith('_')]
                                        logger.info(f"Stream chunk #{chunk_count} part attrs: {part_attrs[:10]}")
                                        # Check for common thinking-related attributes
                                        if hasattr(part, 'thought'):
                                            logger.info(f"  part.thought = {part.thought}")
                                        if hasattr(part, 'thinking'):
                                            logger.info(f"  part.thinking = {part.thinking}")
                                        if hasattr(part, 'text'):
                                            logger.info(f"  part.text[:50] = {str(part.text)[:50]}")
                                    
                                    if hasattr(part, 'thought') and part.thought:
                                        chunk_queue.put({"type": "thinking", "text": str(part.thought)})
                                    elif hasattr(part, 'text') and part.text:
                                        chunk_queue.put({"type": "content", "text": str(part.text)})
                    
                    # Extract token usage (last chunk has final counts)
                    if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                        meta = chunk.usage_metadata
                        token_usage["input_tokens"] = getattr(meta, 'prompt_token_count', 0) or 0
                        token_usage["output_tokens"] = getattr(meta, 'candidates_token_count', 0) or 0
                        token_usage["thinking_tokens"] = getattr(meta, 'thoughts_token_count', 0) or 0
                        token_usage["cached_tokens"] = getattr(meta, 'cached_content_token_count', 0) or 0
                        token_usage["total_tokens"] = (
                            token_usage["input_tokens"] + 
                            token_usage["output_tokens"] + 
                            token_usage["thinking_tokens"]
                        )
                
                # Signal completion
                chunk_queue.put(None)
                
            except Exception as e:
                error_holder[0] = e
                chunk_queue.put(None)
        
        # Start stream in background thread
        thread = threading.Thread(target=stream_in_thread, daemon=True)
        thread.start()
        
        # Yield chunks as they arrive
        try:
            while True:
                try:
                    # Check queue with timeout to allow async yielding
                    chunk = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: chunk_queue.get(timeout=0.1)
                    )
                    
                    if chunk is None:
                        # Stream completed
                        break
                    
                    yield chunk
                    
                except queue.Empty:
                    # No chunk yet, yield control to event loop
                    await asyncio.sleep(0.01)
                    continue
            
            # Check for errors
            if error_holder[0]:
                logger.error(f"Streaming error: {error_holder[0]}")
                raise error_holder[0]
            
            # Yield final token counts
            yield {"type": "done", "tokens": token_usage}
            
        finally:
            thread.join(timeout=1.0)

    async def generate_chat_with_thinking_stream(
        self,
        history: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        model: str = "gemini-3-flash-preview",
        thinking_level: str = "low",
    ):
        """
        Streams SSE-formatted events for chat (thinking + content).
        
        Yields:
            SSE-formatted strings (event: <type>\ndata: <payload>\n\n)
        """
        contents = []
        for msg in history:
            role = msg.get("role", "user")
            if role in ["assistant", "model"]:
                role = "model"
            elif role == "system":
                continue
            
            contents.append(types.Content(
                role=role,
                parts=[types.Part(text=msg.get("content", ""))]
            ))
            
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level=thinking_level
            )
        )
        if system_instruction:
            config.system_instruction = system_instruction

        loop = asyncio.get_event_loop()
        
        try:
            stream = await loop.run_in_executor(
                None,
                lambda: self.client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=config,
                )
            )
            
            accumulated_thinking = ""
            accumulated_content = ""
            token_usage = {}
            
            for chunk in stream:
                if hasattr(chunk, 'candidates') and chunk.candidates:
                    for candidate in chunk.candidates:
                        if hasattr(candidate, 'content') and candidate.content:
                            for part in candidate.content.parts:
                                if hasattr(part, 'thought') and part.thought:
                                    thinking_chunk = str(part.thought)
                                    accumulated_thinking += thinking_chunk
                                    yield f"event: thinking\ndata: {json.dumps({'text': thinking_chunk})}\n\n"
                                    await asyncio.sleep(0)
                                elif hasattr(part, 'text') and part.text:
                                    content_chunk = part.text
                                    accumulated_content += content_chunk
                                    yield f"event: content\ndata: {json.dumps({'text': content_chunk})}\n\n"
                                    await asyncio.sleep(0)
                
                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    token_usage = self._extract_token_usage(chunk)
            
            yield f"event: done\ndata: {json.dumps({'thinking': accumulated_thinking, 'content': accumulated_content, 'tokens': token_usage})}\n\n"
            
        except Exception as e:
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"
    
    async def start_deep_research(
        self,
        topic: str,
        agent: str = "deep-research-pro-preview-12-2025",
    ) -> Dict[str, Any]:
        """Start an asynchronous Deep Research task."""
        try:
            loop = asyncio.get_event_loop()
            interaction = await loop.run_in_executor(
                None,
                lambda: self.client.interactions.create(
                    agent=agent,
                    input=f"Research: {topic}",
                    background=True,
                    config=types.InteractionConfig(store=True),
                )
            )
            
            return {
                "task_id": interaction.id,
                "status": interaction.status if hasattr(interaction, 'status') else "in_progress",
                "message": f"Started research on: {topic}",
            }
            
        except Exception as e:
            logger.error(f"Failed to start deep research: {e}")
            raise Exception(f"Failed to start deep research: {str(e)}")
    
    async def poll_research_status(
        self,
        task_id: str,
        max_wait_seconds: int = 3600,
        poll_interval: int = 10,
    ) -> Dict[str, Any]:
        """Poll for Deep Research completion with exponential backoff."""
        elapsed = 0
        current_interval = poll_interval
        max_interval = 60
        
        while elapsed < max_wait_seconds:
            try:
                loop = asyncio.get_event_loop()
                current_state = await loop.run_in_executor(
                    None,
                    lambda: self.client.interactions.get(id=task_id)
                )
                
                status = current_state.status if hasattr(current_state, 'status') else "unknown"
                
                if status == "completed":
                    result_text = ""
                    if current_state.outputs:
                        for output in current_state.outputs:
                            if hasattr(output, 'text'):
                                result_text += output.text
                    return {"status": "completed", "result": result_text}
                    
                elif status == "failed":
                    return {
                        "status": "failed",
                        "result": None,
                        "error": getattr(current_state, 'error', 'Unknown error'),
                    }
                    
                elif status == "cancelled":
                    return {"status": "cancelled", "result": None}
                    
            except Exception as e:
                logger.warning(f"Polling error: {e}")
            
            await asyncio.sleep(current_interval)
            elapsed += current_interval
            current_interval = min(current_interval + 5, max_interval)
        
        return {"status": "timeout", "result": None}
    
    async def process_document(
        self,
        file_path: str,
        prompt: str = "Analyze this document for key presentation points.",
        model: str = "gemini-3-flash-preview",
        thinking_level: str = "low",
    ) -> Dict[str, Any]:
        """Process a document (PDF, image, etc.) using Gemini's native multimodal."""
        path = Path(file_path)
        
        mime_types = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }
        mime_type = mime_types.get(path.suffix.lower(), "application/octet-stream")
        
        with open(file_path, "rb") as f:
            file_data = base64.standard_b64encode(f.read()).decode("utf-8")
        
        multimodal_input = [
            {"text": prompt},
            {"inline_data": {"mime_type": mime_type, "data": file_data}}
        ]
        
        return await self.generate_with_thinking(
            prompt=multimodal_input,
            model=model,
            thinking_level=thinking_level,
        )
