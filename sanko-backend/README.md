# SankoSlides Backend

> AI-powered academic slide generation using CrewAI multi-agent orchestration and Google Gemini 3.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![CrewAI](https://img.shields.io/badge/CrewAI-Flow-orange.svg)](https://crewai.com/)

## Overview

SankoSlides Backend is a FastAPI service that orchestrates AI agents to generate professional academic presentations. It features:

- **Multi-Agent Pipeline**: 7 specialized AI agents working in sequence
- **Event-Driven Flow**: Pause points for user review and modification
- **Real-Time Streaming**: SSE progress updates during generation
- **Template System**: 10+ semantic HTML slide layouts
- **Quality Assurance**: Visual QA with 95% pass threshold
- **Token Metrics**: Full cost and usage tracking for frontend display

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SankoSlides Backend                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │  Clarifier  │───▶│   Outliner  │───▶│   Planner   │             │
│  │  (Flash)    │    │  (Flash)    │    │   (Pro)     │             │
│  └─────────────┘    └──────┬──────┘    └──────┬──────┘             │
│                            │                   │                    │
│                      [User Review]             │                    │
│                            │                   ▼                    │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   Helper    │◀──▶│  Visual QA  │◀───│  Generator  │◀───Refiner  │
│  │   (Pro)     │    │  (Flash)    │    │  (Flash)    │    (Pro)    │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                    ┌───────────────────────────┐
                    │     Render Service        │
                    │  (LaTeX, Mermaid, Code)   │
                    └───────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL (for session persistence)
- [Render Service](../sanko-render-service/) running on port 3001

### Installation

```bash
# Clone and navigate
cd sanko-backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env
# Edit .env with your API keys
```

### Environment Variables

```env
# Required
GEMINI_API_KEY=your_gemini_api_key

# Database (optional - uses in-memory if not set)
DATABASE_URL=postgresql://user:pass@localhost:5432/sankoslides

# Services
RENDER_SERVICE_URL=http://localhost:3001
FRONTEND_URL=http://localhost:3000

# Server
PORT=8000
DEBUG=true
DEV_MODE=true
```

### Run the Server

```bash
# Development with hot reload
uvicorn app.main:app --reload --port 8000

# Or use the run script
python run.py
```

### Verify Installation

- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

## API Endpoints

### Generation Flow

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generation/start` | POST | Create new session |
| `/api/generation/clarify/{id}` | POST | Multi-turn clarification |
| `/api/generation/outline/{id}` | POST | Generate outline for review |
| `/api/generation/approve-outline/{id}` | POST | Approve/modify outline |
| `/api/generation/generate/{id}` | POST | Start async generation |
| `/api/generation/stream/{id}` | GET | SSE progress stream |
| `/api/generation/status/{id}` | GET | Poll session status |
| `/api/generation/result/{id}` | GET | Get final presentation |

### Metrics & Debugging

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/generation/metrics/{id}` | GET | Full token usage per agent |
| `/api/generation/metrics/{id}/summary` | GET | Quick usage summary |
| `/api/generation/quick-start` | POST | Skip clarification (demo) |

### Utility

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API info |
| `/health` | GET | Health check |

## Project Structure

```
sanko-backend/
├── app/
│   ├── main.py                 # FastAPI entry point
│   ├── api/routers/            # API endpoints
│   │   └── generation.py       # Generation flow endpoints
│   ├── core/                   # Core utilities
│   │   ├── config.py           # Environment configuration
│   │   ├── database.py         # PostgreSQL models
│   │   └── logging.py          # Structured logging
│   ├── models/                 # Pydantic schemas
│   │   └── schemas.py          # All data models
│   ├── crew/                   # CrewAI components
│   │   ├── agents/             # 7 specialized agents
│   │   ├── flows/              # Flow orchestration
│   │   └── tools/              # Agent tools
│   ├── clients/                # External service clients
│   │   ├── gemini/             # Gemini API wrapper
│   │   └── render.py           # Render service client
│   └── templates/              # HTML slide templates
│       ├── base.py             # Base template class
│       └── layouts/            # 10 layout types
├── docs/                       # Documentation
├── tests/                      # Test suite
├── alembic/                    # Database migrations
└── requirements.txt            # Dependencies
```

## Documentation

See the [`docs/`](./docs/) folder for detailed documentation:

- [API Reference](./docs/api-reference.md) - Complete endpoint documentation
- [Agents Guide](./docs/agents.md) - How the 7 agents work
- [Flow Architecture](./docs/flow-architecture.md) - Pipeline and pause points
- [Templates](./docs/templates.md) - Slide template system
- [Metrics](./docs/metrics.md) - Token tracking and costs
- [Frontend Integration](./docs/frontend-integration.md) - Connecting to frontend

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Code Quality

```bash
# Type checking
mypy app/

# Linting
ruff check app/
```

## License

MIT License - see [LICENSE](./LICENSE) for details.
