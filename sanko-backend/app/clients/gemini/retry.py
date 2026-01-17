"""
Gemini API Retry Utilities

Provides retry logic with exponential backoff for handling transient
Gemini API errors like 503 (model overloaded), 429 (rate limited),
and connection issues.

Usage:
    from app.clients.gemini.retry import gemini_retry, gemini_retry_async
    
    @gemini_retry
    def sync_gemini_call():
        return client.generate_content(...)
    
    @gemini_retry_async
    async def async_gemini_call():
        return await model.generate_content_async(...)
"""

import asyncio
import functools
import random
from typing import Callable, TypeVar, Any, Tuple, Type

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_exception,
    before_sleep_log,
    RetryError,
)

from app.core.logging import get_logger

logger = get_logger(__name__)

# Type vars for decorator
F = TypeVar('F', bound=Callable[..., Any])


# ===========================================================================
# Error Detection
# ===========================================================================

def is_retryable_gemini_error(exception: BaseException) -> bool:
    """
    Determine if a Gemini API error is retryable.
    
    Retryable errors:
    - 503 Service Unavailable (model overloaded)
    - 429 Too Many Requests (rate limited)
    - 500 Internal Server Error (transient)
    - Connection/timeout errors
    
    Non-retryable errors:
    - 400 Bad Request
    - 401/403 Auth errors
    - 404 Not Found
    """
    error_str = str(exception).lower()
    
    # Check for specific HTTP status codes
    retryable_codes = ['503', '429', '500', '502', '504']
    if any(code in str(exception) for code in retryable_codes):
        return True
    
    # Check for common transient error messages
    retryable_messages = [
        'overloaded',
        'rate limit',
        'ratelimit',
        'too many requests',
        'temporarily unavailable',
        'service unavailable',
        'try again later',
        'connection reset',
        'connection refused',
        'timeout',
        'timed out',
        'unavailable',
    ]
    
    if any(msg in error_str for msg in retryable_messages):
        return True
    
    # Check for connection/network errors
    exception_type_name = type(exception).__name__.lower()
    network_errors = [
        'timeout',
        'connectionerror',
        'connecterror',
        'networkerror',
        'httpxerror',
        'oserror',
        'socketerror',
    ]
    
    if any(err in exception_type_name for err in network_errors):
        return True
    
    return False


def extract_retry_after(exception: BaseException) -> int:
    """
    Extract retry-after delay from error message if present.
    
    Returns suggested wait time in seconds, or 0 if not found.
    """
    import re
    error_str = str(exception)
    
    # Look for "retry in X seconds" or "retry after X seconds"
    patterns = [
        r'retry in (\d+)',
        r'retry after (\d+)',
        r'wait (\d+) second',
        r'try again in (\d+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_str.lower())
        if match:
            return int(match.group(1))
    
    return 0


# ===========================================================================
# Retry Configuration
# ===========================================================================

# Default retry settings
DEFAULT_MAX_ATTEMPTS = 4
DEFAULT_MIN_WAIT = 1  # seconds
DEFAULT_MAX_WAIT = 30  # seconds
DEFAULT_MULTIPLIER = 2


def get_retry_config(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
    multiplier: float = DEFAULT_MULTIPLIER,
):
    """
    Get tenacity retry configuration for Gemini API calls.
    
    Uses exponential backoff with jitter:
    - Attempt 1: immediate
    - Attempt 2: wait 1-2s
    - Attempt 3: wait 2-4s
    - Attempt 4: wait 4-8s
    """
    return {
        "stop": stop_after_attempt(max_attempts),
        "wait": wait_exponential(
            multiplier=multiplier,
            min=min_wait,
            max=max_wait,
        ),
        "retry": retry_if_exception(is_retryable_gemini_error),
        "before_sleep": before_sleep_log(logger, "WARNING"),
        "reraise": True,
    }


# ===========================================================================
# Sync Retry Decorator
# ===========================================================================

def gemini_retry(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
) -> Callable[[F], F]:
    """
    Decorator for retrying synchronous Gemini API calls.
    
    Usage:
        @gemini_retry()
        def call_gemini():
            return client.generate_content(...)
    
    Args:
        max_attempts: Maximum number of retry attempts (default 4)
        min_wait: Minimum wait between retries in seconds (default 1)
        max_wait: Maximum wait between retries in seconds (default 30)
    """
    config = get_retry_config(max_attempts, min_wait, max_wait)
    
    def decorator(func: F) -> F:
        @functools.wraps(func)
        @retry(**config)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    
    return decorator


# ===========================================================================
# Async Retry Decorator
# ===========================================================================

def gemini_retry_async(
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
) -> Callable[[F], F]:
    """
    Decorator for retrying asynchronous Gemini API calls.
    
    Usage:
        @gemini_retry_async()
        async def call_gemini():
            return await model.generate_content_async(...)
    
    Args:
        max_attempts: Maximum number of retry attempts (default 4)
        min_wait: Minimum wait between retries in seconds (default 1)
        max_wait: Maximum wait between retries in seconds (default 30)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not is_retryable_gemini_error(e):
                        # Non-retryable error, raise immediately
                        raise
                    
                    if attempt == max_attempts:
                        # Last attempt, raise the error
                        logger.error(f"Gemini API failed after {max_attempts} attempts: {e}")
                        raise
                    
                    # Calculate wait time with exponential backoff + jitter
                    base_wait = min(min_wait * (2 ** (attempt - 1)), max_wait)
                    jitter = random.uniform(0, base_wait * 0.1)  # 10% jitter
                    wait_time = base_wait + jitter
                    
                    # Check for API-suggested retry time
                    suggested_wait = extract_retry_after(e)
                    if suggested_wait > 0:
                        wait_time = max(wait_time, suggested_wait)
                    
                    logger.warning(
                        f"Gemini API error (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    
                    await asyncio.sleep(wait_time)
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper  # type: ignore
    
    return decorator


# ===========================================================================
# Utility Functions
# ===========================================================================

async def retry_gemini_call_async(
    func: Callable[..., Any],
    *args,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
    **kwargs,
) -> Any:
    """
    Retry a Gemini API call with exponential backoff.
    
    Functional alternative to the decorator for one-off calls.
    
    Usage:
        result = await retry_gemini_call_async(
            model.generate_content_async,
            prompt,
            generation_config=config,
        )
    """
    @gemini_retry_async(max_attempts, min_wait, max_wait)
    async def wrapped():
        return await func(*args, **kwargs)
    
    return await wrapped()


def retry_gemini_call_sync(
    func: Callable[..., Any],
    *args,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    min_wait: float = DEFAULT_MIN_WAIT,
    max_wait: float = DEFAULT_MAX_WAIT,
    **kwargs,
) -> Any:
    """
    Retry a synchronous Gemini API call with exponential backoff.
    
    Functional alternative to the decorator for one-off calls.
    """
    @gemini_retry(max_attempts, min_wait, max_wait)
    def wrapped():
        return func(*args, **kwargs)
    
    return wrapped()
