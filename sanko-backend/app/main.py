"""
SankoSlides Backend - FastAPI Application Entry Point

This is the main entry point for the SankoSlides AI generation backend.
It orchestrates multi-agent workflows using CrewAI and Google Gemini.
"""

# CRITICAL: Windows asyncio event loop policy fix
# Must be set BEFORE any other asyncio imports or operations
# This enables Playwright subprocess support on Windows
import sys
if sys.platform == 'win32':
    import asyncio
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.core.config import settings
from app.core.logging import get_logger
from app.core.otel import setup_otel, instrument_fastapi
from app.api.routers.generation import router as generation_router
from app.export.router import router as export_router
# from app.routers.universities import router as universities_router
from app.api.routers.templates import router as templates_router

# Initialize logging
logger = get_logger(__name__)

# OpenTelemetry (traces) - enabled via env vars.
# This must run before instrumenting FastAPI.
_otel_enabled = setup_otel(service_name=os.getenv("OTEL_SERVICE_NAME", "sanko-backend"))

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs on startup and shutdown.
    """
    # Startup
    logger.info("SankoSlides Backend starting...")
    logger.info(f"Frontend URL: {settings.frontend_url}")
    logger.info(f"Debug Mode: {settings.debug}")
    logger.info(f"Dev Mode: {settings.dev_mode}")
    
    # Validate critical configuration
    if not settings.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set. AI features will not work.")
    else:
        logger.info("Gemini API key configured")
    
    yield
    
    # Shutdown
    logger.info("SankoSlides Backend shutting down...")


# Create FastAPI application
app = FastAPI(
    title="SankoSlides API",
    description="AI-powered slide generation using CrewAI and Google Gemini",
    version="0.2.0",  # Bumped for CrewAI migration
    lifespan=lifespan,
)

# Instrument request spans if tracing is enabled.
if _otel_enabled:
    instrument_fastapi(app)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(generation_router, prefix="/api", tags=["Generation"])
app.include_router(export_router, prefix="/api", tags=["Export"])
# app.include_router(universities_router, prefix="/api", tags=["Universities"])
app.include_router(templates_router, prefix="/api", tags=["Templates"])


@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "SankoSlides API",
        "version": "0.2.0",
        "status": "running",
        "architecture": "CrewAI Multi-Agent",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
