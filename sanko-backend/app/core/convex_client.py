"""
Convex Client Wrapper

Provides a singleton instance of the Convex client for the backend.
Uses CONVEX_URL from environment variables.
"""

import os
from convex import ConvexClient
from app.core.config import settings

# Global client instance
_client = None

def get_convex_client() -> ConvexClient:
    """
    Get or create the Convex client singleton.
    """
    global _client
    if _client is None:
        # Construct the URL:
        # If running locally, we might need a specific URL, but usually it's passed via ENV.
        # Ensure your .env has CONVEX_URL (usually from `npx convex dev`)
        url = os.getenv("CONVEX_URL")
        if not url:
            # Fallback or error
            # For dev, we might paste the url manually or use a script to sync it
            raise ValueError("CONVEX_URL environment variable is not set. Please run 'npx convex dev' in frontend and copy the URL.")
            
        _client = ConvexClient(url)
        
    return _client
