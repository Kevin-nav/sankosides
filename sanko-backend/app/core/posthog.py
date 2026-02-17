"""
PostHog (server-side) analytics.

We use this for high-signal events that must exist even if the browser blocks tracking,
especially cost/usage telemetry (token counts, per-agent totals).

Security/PII policy:
- Do NOT send raw prompts, PDF contents, slide HTML, or auth tokens.
- Keep properties small and structured.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional


def _env_truthy(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_client():
    try:
        import posthog  # type: ignore
    except Exception:
        return None
    return posthog


def is_enabled() -> bool:
    if _env_truthy("POSTHOG_DISABLED", "false"):
        return False
    key = os.getenv("POSTHOG_PROJECT_API_KEY", "").strip()
    return bool(key)


def configure() -> bool:
    """
    Configure the global posthog client from env vars.
    Safe to call multiple times.
    """
    if not is_enabled():
        return False

    client = _get_client()
    if not client:
        return False

    if getattr(client, "_sanko_configured", False):
        return True

    client.project_api_key = os.getenv("POSTHOG_PROJECT_API_KEY", "").strip()
    # For PostHog Cloud, the recommended host is typically an ingestion endpoint like:
    # - https://us.i.posthog.com
    # - https://eu.i.posthog.com
    client.host = os.getenv("POSTHOG_HOST", "https://us.i.posthog.com").strip()

    # Keep server-side capture non-blocking.
    # The python client batches internally; we keep defaults.
    setattr(client, "_sanko_configured", True)
    return True


def capture(event: str, distinct_id: str, properties: Optional[Dict[str, Any]] = None) -> None:
    """
    Best-effort capture. Never raises.
    """
    try:
        if not configure():
            return
        client = _get_client()
        if not client:
            return
        client.capture(distinct_id=distinct_id, event=event, properties=properties or {})
    except Exception:
        return


def build_common_props(**extra: Any) -> Dict[str, Any]:
    props: Dict[str, Any] = {}

    env = os.getenv("DEPLOYMENT_ENV", "") or os.getenv("ENVIRONMENT", "") or ""
    if not env:
        # Reuse OTel environment tag if present.
        attrs = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "")
        # e.g. "deployment.environment=prod,service.version=..."
        for part in (attrs or "").split(","):
            part = part.strip()
            if part.startswith("deployment.environment="):
                env = part.split("=", 1)[1].strip()
                break

    if env:
        props["deployment_environment"] = env

    for k, v in extra.items():
        if v is None:
            continue
        props[k] = v
    return props

