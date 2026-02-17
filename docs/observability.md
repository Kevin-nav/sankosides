# Observability (Honeycomb via OpenTelemetry)

This repo uses OpenTelemetry (OTel) for traces and Honeycomb as the hosted backend.

## Components

- `docker-compose.observability.yml`: runs an OTLP collector locally or on a server
- `observability/otel-collector-config.yaml`: receives OTLP and exports to Honeycomb
- `sanko-backend`: FastAPI tracing
- `sanko-render-service`: Express tracing

## Honeycomb setup

1. Create a Honeycomb environment and get an API key.
2. Choose a dataset name per environment, for example:
   - `sankoslides-dev`
   - `sankoslides-prod`

## Run collector (dev)

Set env vars in your shell, or put them in the repo root `.env` (Docker Compose reads it automatically):

```powershell
$env:HONEYCOMB_API_KEY="..."
$env:HONEYCOMB_DATASET="sankoslides-dev"
docker compose -f .\docker-compose.observability.yml up -d
```

Health check:

```powershell
Invoke-RestMethod http://localhost:13133/
```

Git Bash:

```bash
curl http://localhost:13133/
```

## App env vars

Point services to the collector:

- `OTEL_ENABLED=true`
- `OTEL_LOGS_ENABLED=true` (optional; exports app logs via OTLP too)
- `OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317` (gRPC; `http://localhost:4317` also accepted)
- `OTEL_SERVICE_NAME=sanko-backend` (or `sanko-render-service`)
- `OTEL_RESOURCE_ATTRIBUTES=deployment.environment=dev`

## Production

Recommended production layout:

- Run the collector as a sidecar (same host/network) as your services.
- Use `HONEYCOMB_DATASET=sankoslides-prod`.
- Configure sampling in the collector or per-service via standard `OTEL_*` env vars.
