# Gemini PDF Synthesis Test Framework

Comprehensive testing framework for achieving near-zero failure rate in PDF synthesis.

## Features

- **Graceful shutdown**: Press Ctrl+C to stop after current run (saves progress)
- **Incremental saves**: Results saved after each run, not just at end
- **Activity logging**: Real-time visibility into what's happening
- **Live dashboard**: Streamlit dashboard with auto-refresh support
- **Multiple strategies**: Compare different synthesis approaches

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set API key (choose one method):
# Option 1: Environment variable
export GEMINI_API_KEY=your_api_key_here

# Option 2: Use .env file (create in this directory or use sanko-backend/.env)

# Run tests (all strategies, 3 runs each)
python runner.py --runs 3

# View results dashboard
streamlit run dashboard.py
```

## Configuration

### API Key

The framework looks for API keys in this order:
1. `--api-key` command line argument
2. `GEMINI_API_KEY` environment variable
3. `GOOGLE_API_KEY` environment variable
4. `.env` file in this directory
5. `.env` file in `sanko-backend/`

### Test Configuration

```bash
# View current configuration
python config.py

# Override default model
export GEMINI_MODEL=gemini-3-pro-preview
```

## Usage

```bash
# List available strategies
python runner.py --list-strategies

# List available models
python runner.py --list-models

# Test specific strategy
python runner.py --strategy baseline --runs 5

# Test specific PDF
python runner.py --pdf "Calculus" --runs 3

# Verbose output
python runner.py --runs 3 --verbose

# Full test suite
python runner.py --runs 5
```

## Graceful Shutdown

- Press Ctrl+C once to finish current run and save progress
- Press Ctrl+C twice to force quit immediately
- Progress is saved incrementally after each run

## Strategies

| Strategy | Model | Description |
|----------|-------|-------------|
| `baseline` | gemini-3-flash-preview | Single prompt, full PDF, temp=0.0 |
| `baseline_t01` | gemini-3-flash-preview | Temperature 0.1 |
| `baseline_t02` | gemini-3-flash-preview | Temperature 0.2 |
| `chunked_10` | gemini-3-flash-preview | 10 pages/chunk with 2-page overlap |
| `chunked_5` | gemini-3-flash-preview | 5 pages/chunk with 1-page overlap |
| `two_phase` | gemini-3-flash-preview | Extract structure first, then content |
| `model_3_pro` | gemini-3-pro-preview | Gemini 3 Pro (stronger reasoning) |
| `model_25_pro` | gemini-2.5-pro | Legacy: Gemini 2.5 Pro |
| `model_25_flash` | gemini-2.5-flash | Legacy: Gemini 2.5 Flash |

## Available Models (Dec 2025)

| Model API Name | Description |
|----------------|-------------|
| `gemini-3-flash-preview` | Fast, frontier-class performance (default) |
| `gemini-3-pro-preview` | Complex agentic problems, strong coding/reasoning |
| `gemini-2.5-flash` | Previous generation Flash |
| `gemini-2.5-pro` | Previous generation Pro |

## Metrics Tracked

- **Performance**: API latency, total time, parse time
- **Quality**: Section count, content length, LaTeX/visuals extraction
- **Failure**: Error types, truncation detection, retries
- **Response**: JSON validity, truncation indicators

## Results

Results are saved to `results/run_YYYY-MM-DD_HH-MM-SS/`:
- `runs.json` - Individual run metrics
- `summary.json` - Aggregated statistics
- `activity.json` - Real-time activity log
- `status.json` - Current run status (for live dashboard)

## Dashboard

The Streamlit dashboard provides:
- Current run status (running/complete)
- Real-time activity log
- Success rate by strategy/PDF
- Error type breakdown
- Quality metrics comparison
- Performance timeline
- Downloadable reports (CSV, JSON)

### Live Monitoring

Enable "Auto-refresh" in the dashboard sidebar to see updates in real-time while tests are running.

## File Structure

```
test_synthesis/
├── config.py       # Configuration and API key loading
├── metrics.py      # Metrics collection and data classes
├── strategies.py   # Synthesis strategy implementations
├── runner.py       # Main test runner with graceful shutdown
├── dashboard.py    # Streamlit visualization dashboard
├── requirements.txt
└── results/        # Test run results (created automatically)
    └── run_YYYY-MM-DD_HH-MM-SS/
        ├── runs.json
        ├── summary.json
        ├── activity.json
        └── status.json
```
