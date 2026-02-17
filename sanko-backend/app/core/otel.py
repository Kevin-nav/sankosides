"""
OpenTelemetry setup for SankoSlides backend.

Design goals:
- Safe to import even if OTel packages are not installed (no hard dependency at runtime).
- Enable via env (OTEL_ENABLED=true) and a configured OTLP endpoint.
- Minimal, pragmatic defaults that work in dev and production.
"""

from __future__ import annotations

import os
import logging
from typing import Optional


def _env_truthy(name: str, default: str = "false") -> bool:
    value = os.getenv(name, default)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def setup_otel(service_name: str) -> bool:
    """
    Configure OpenTelemetry tracing and instrument common libraries.

    Returns:
        True if OTel was configured and enabled, False otherwise.
    """
    enabled = _env_truthy("OTEL_ENABLED", "false")
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()

    if not enabled:
        return False
    if not otlp_endpoint:
        # Allow OTEL_ENABLED=true to be set broadly without breaking startup.
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
    except Exception:
        # Dependencies not installed or partially installed.
        return False

    # Configure provider once.
    provider = trace.get_tracer_provider()
    if getattr(provider, "_sanko_configured", False):
        return True

    resource_attrs = {"service.name": service_name}
    # If OTEL_RESOURCE_ATTRIBUTES is set, merge it (simple key=value parser).
    raw_attrs = os.getenv("OTEL_RESOURCE_ATTRIBUTES", "").strip()
    if raw_attrs:
        for part in raw_attrs.split(","):
            part = part.strip()
            if not part or "=" not in part:
                continue
            k, v = part.split("=", 1)
            k = k.strip()
            v = v.strip()
            if k and v and k not in resource_attrs:
                resource_attrs[k] = v
    resource = Resource.create(resource_attrs)

    tracer_provider = TracerProvider(resource=resource)
    # Normalize endpoint for OTLP/gRPC exporter:
    # - gRPC expects host:port (no scheme)
    # - allow users to provide http(s)://host:port for convenience
    endpoint = otlp_endpoint
    endpoint_l = endpoint.lower()
    insecure = True
    if endpoint_l.startswith("https://"):
        insecure = False
        endpoint = endpoint[8:]
    elif endpoint_l.startswith("http://"):
        insecure = True
        endpoint = endpoint[7:]
    exporter = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
    tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(tracer_provider)

    # Optional: OpenTelemetry logs export (OTLP/gRPC) so logs land in Honeycomb too.
    # Enable via OTEL_LOGS_ENABLED=true (defaults to OTEL_ENABLED).
    logs_enabled = _env_truthy("OTEL_LOGS_ENABLED", "true")
    if logs_enabled:
        try:
            from opentelemetry._logs import set_logger_provider  # type: ignore
            from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler  # type: ignore
            from opentelemetry.sdk._logs.export import BatchLogRecordProcessor  # type: ignore
            from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter  # type: ignore

            # Share the same endpoint/insecure decision as traces.
            log_exporter = OTLPLogExporter(endpoint=endpoint, insecure=insecure)
            logger_provider = LoggerProvider(resource=resource)
            logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
            set_logger_provider(logger_provider)

            otel_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)

            # Attach to the main application loggers without changing existing formatting/handlers.
            # Note: many app loggers have propagate=False, so root-only isn't enough.
            target_names = {
                "",  # root
                "app",
                "app.pipeline",
                "app.routers",
                "app.services",
                "app.tools",
                "uvicorn",
                "uvicorn.error",
                "uvicorn.access",
            }
            for name in target_names:
                lg = logging.getLogger(name) if name else logging.getLogger()
                if any(type(h).__name__ == type(otel_handler).__name__ for h in lg.handlers):
                    continue
                lg.addHandler(otel_handler)

            setattr(trace.get_tracer_provider(), "_sanko_logs_configured", True)
        except Exception:
            pass

    # Instrument common libraries (safe to call multiple times; they are idempotent in practice).
    try:
        HTTPXClientInstrumentor().instrument()
    except Exception:
        pass
    try:
        RequestsInstrumentor().instrument()
    except Exception:
        pass
    try:
        AioHttpClientInstrumentor().instrument()
    except Exception:
        pass

    # Mark configured so reloads don't duplicate processors.
    setattr(trace.get_tracer_provider(), "_sanko_configured", True)

    # Expose the FastAPI instrumentor to be used by app startup.
    setattr(setup_otel, "_fastapi_instrumentor", FastAPIInstrumentor)
    return True


def instrument_fastapi(app) -> None:
    """
    Instrument a FastAPI app if OTel has been enabled via setup_otel().
    """
    instrumentor = getattr(setup_otel, "_fastapi_instrumentor", None)
    if not instrumentor:
        return

    def _server_request_hook(span, scope):
        # ASGI scope hook; keep it PII-safe. Avoid logging raw topics/prompts, auth headers, etc.
        try:
            if not span or not span.is_recording():
                return

            path_params = scope.get("path_params") or {}
            if isinstance(path_params, dict):
                for key in ("session_id", "file_hash", "template_id", "theme_id"):
                    value = path_params.get(key)
                    if isinstance(value, str) and value:
                        span.set_attribute(f"sanko.{key}", value)

            # Allowlist a few safe query params (avoid topic, arbitrary user input).
            raw_qs = scope.get("query_string") or b""
            if raw_qs:
                try:
                    from urllib.parse import parse_qs

                    qs = parse_qs(raw_qs.decode("utf-8", errors="ignore"))
                    for key in ("mode", "format"):
                        value = qs.get(key, [None])[0]
                        if isinstance(value, str) and value:
                            span.set_attribute(f"sanko.query.{key}", value)
                except Exception:
                    pass
        except Exception:
            return

    try:
        instrumentor.instrument_app(app, server_request_hook=_server_request_hook)
    except Exception:
        # Don't block app startup due to tracing issues.
        return
