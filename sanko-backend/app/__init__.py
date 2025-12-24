# ==============================================================================
# SankoSlides Backend Package
#
# CRITICAL: Windows asyncio event loop policy fix
# This MUST be set before any asyncio-related imports occur.
# When uvicorn uses --reload, it spawns a subprocess that imports this module
# fresh, so we need to set the policy here to catch it early.
# ==============================================================================

import sys

if sys.platform == 'win32':
    import asyncio
    # Only set if not already set correctly
    policy = asyncio.get_event_loop_policy()
    if not isinstance(policy, asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
