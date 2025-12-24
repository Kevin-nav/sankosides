# SankoSlides Render Service

Node.js microservice for deterministic STEM rendering.

## Setup

```bash
cd sanko-render-service
npm install
npm start
```

The service runs on `http://localhost:3001`.

## Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/render/latex` | POST | LaTeX → SVG |
| `/render/mermaid` | POST | Mermaid → SVG |
| `/render/citation` | POST | Metadata → Formatted string |
| `/render/batch` | POST | Batch processing |

## Why Code Instead of AI?

Citation formatting and equation rendering must be **deterministic**:
- Zero hallucination in formatting
- Perfect IEEE/APA/Harvard compliance
- Vector-quality math in PowerPoint

The LLM finds the data; code formats it correctly.

## Example Usage

### LaTeX
```bash
curl -X POST http://localhost:3001/render/latex \
  -H "Content-Type: application/json" \
  -d '{"latex": "E = mc^2"}'
```

### Citation
```bash
curl -X POST http://localhost:3001/render/citation \
  -H "Content-Type: application/json" \
  -d '{"citations": [{"author": "Smith", "year": "2023", "title": "Deep Learning", "source": "Journal"}], "style": "apa"}'
```
