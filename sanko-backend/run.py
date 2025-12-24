"""
SankoSlides Backend - Development Server Entry Point

This script sets the Windows-specific asyncio event loop policy BEFORE
starting uvicorn, which is required for Playwright to work on Windows.

Usage:
    python run.py  # Default: --reload --port 8080
    python run.py --port 3000 --no-reload
"""

import sys

# ==============================================================================
# CRITICAL: Set Windows event loop policy BEFORE importing uvicorn
# This enables Playwright subprocess support on Windows
# ==============================================================================
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    print("✓ Windows ProactorEventLoop policy set")

import argparse


def main():
    parser = argparse.ArgumentParser(description="Run SankoSlides Backend")
    parser.add_argument("--port", type=int, default=8080, help="Port to run on")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")
    args = parser.parse_args()

    # Import uvicorn AFTER setting the event loop policy
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        loop="asyncio",  # Use asyncio loop (respects our policy)
    )


if __name__ == "__main__":
    main()
