"""
Session Store

JSON file-based session persistence for development.
Extracted from generation.py for better modularity.
"""

import os
import json
import asyncio
from typing import Dict, Any

from app.logging_config import get_logger

logger = get_logger(__name__)

SESSION_FILE = "sessions.json"

# In-memory session storage
sessions: Dict[str, Dict[str, Any]] = {}

# Event queues for real-time streaming
session_events: Dict[str, asyncio.Queue] = {}


def load_sessions() -> Dict[str, Dict[str, Any]]:
    """Load sessions from local JSON file."""
    global sessions
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, "r") as f:
                sessions = json.load(f)
                return sessions
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            return {}
    return {}


def save_sessions() -> None:
    """Save sessions to local JSON file."""
    try:
        with open(SESSION_FILE, "w") as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save sessions: {e}")


def get_session(session_id: str) -> Dict[str, Any] | None:
    """Get a session by ID."""
    return sessions.get(session_id)


def create_session(session_id: str, data: Dict[str, Any]) -> None:
    """Create a new session."""
    sessions[session_id] = data
    save_sessions()


def update_session(session_id: str, updates: Dict[str, Any]) -> None:
    """Update an existing session."""
    if session_id in sessions:
        sessions[session_id].update(updates)
        save_sessions()


def delete_session(session_id: str) -> None:
    """Delete a session."""
    if session_id in sessions:
        del sessions[session_id]
        save_sessions()


# Initialize sessions on module load
sessions = load_sessions()
