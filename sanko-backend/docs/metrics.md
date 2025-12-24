# Token Metrics & Cost Tracking

Documentation for tracking token usage and costs across the generation pipeline.

## Table of Contents

- [Overview](#overview)
- [Pricing](#pricing)
- [Token Usage Model](#token-usage-model)
- [Metrics Collection](#metrics-collection)
- [API Endpoints](#api-endpoints)
- [Frontend Integration](#frontend-integration)
- [Cost Optimization](#cost-optimization)

---

## Overview

SankoSlides tracks all Gemini API token usage to:

- Display costs in the frontend testing ground
- Monitor per-agent token consumption
- Identify optimization opportunities
- Enable billing and usage limits

```
┌─────────────────────────────────────────────────────────┐
│                   Generation Pipeline                   │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Agent Call ──▶ Gemini API ──▶ Response               │
│        │                            │                   │
│        ▼                            ▼                   │
│   ┌──────────┐              ┌──────────────┐            │
│   │  Timer   │              │ usage_metadata│           │
│   └────┬─────┘              └──────┬───────┘            │
│        │                           │                    │
│        └─────────┬─────────────────┘                    │
│                  ▼                                      │
│         ┌────────────────┐                              │
│         │ MetricsCollector│                             │
│         │                │                              │
│         │ - input_tokens │                              │
│         │ - output_tokens│                              │
│         │ - thinking_tok │                              │
│         │ - duration_ms  │                              │
│         │ - cost_usd     │                              │
│         └────────────────┘                              │
│                  │                                      │
│                  ▼                                      │
│         ┌────────────────┐                              │
│         │  SessionMetrics │───▶ /metrics/{session_id}  │
│         └────────────────┘                              │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Pricing

### Gemini 3 API Pricing (December 2025)

| Model | Input (per 1M) | Output (per 1M) | Notes |
|-------|----------------|-----------------|-------|
| **Gemini 3 Flash** | $0.50 | $3.00 | Fast, efficient |
| **Gemini 3 Pro** (≤200K) | $2.00 | $12.00 | High reasoning |
| **Gemini 3 Pro** (>200K) | $4.00 | $18.00 | Long context |

### Cost Calculation

```python
def calculate_cost(usage: TokenUsage, long_context: bool = False) -> float:
    tier = MODEL_TO_TIER.get(usage.model, "flash")
    
    if tier == "pro" and long_context:
        input_price = 4.00  # per 1M
        output_price = 18.00
    elif tier == "pro":
        input_price = 2.00
        output_price = 12.00
    else:  # flash
        input_price = 0.50
        output_price = 3.00
    
    input_cost = (usage.input_tokens / 1_000_000) * input_price
    output_cost = (usage.output_tokens / 1_000_000) * output_price
    # Thinking tokens billed at output rate
    thinking_cost = (usage.thinking_tokens / 1_000_000) * output_price
    
    return input_cost + output_cost + thinking_cost
```

### Example Cost Breakdown

| Agent | Model | Input | Output | Thinking | Cost |
|-------|-------|-------|--------|----------|------|
| Clarifier | Flash | 3,000 | 1,500 | 500 | $0.0075 |
| Outliner | Flash | 4,000 | 2,000 | 300 | $0.0089 |
| Planner | Pro | 8,000 | 6,000 | 2,000 | $0.112 |
| Refiner | Pro | 10,000 | 4,000 | 1,500 | $0.086 |
| Generator | Flash | 5,000 | 8,000 | 1,000 | $0.0295 |
| Visual QA | Flash | 6,000 | 2,000 | 500 | $0.0105 |
| **Total** | | **36,000** | **23,500** | **5,800** | **$0.254** |

---

## Token Usage Model

### TokenUsage

Represents a single API call's token usage:

```python
class TokenUsage(BaseModel):
    input_tokens: int = 0      # Prompt tokens
    output_tokens: int = 0     # Response tokens
    thinking_tokens: int = 0   # Chain-of-thought tokens
    model: str = ""            # Model name
    timestamp: datetime
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens + self.thinking_tokens
    
    def calculate_cost(self, long_context: bool = False) -> float:
        # ... cost calculation
```

### AgentMetrics

Aggregated metrics for a single agent:

```python
class AgentMetrics(BaseModel):
    agent_name: str
    calls: int = 0                    # Number of API calls
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_thinking_tokens: int = 0
    total_cost_usd: float = 0.0
    total_duration_ms: int = 0
    avg_duration_ms: float = 0.0
    call_history: List[TokenUsage]    # Last 10 calls
```

### SessionMetrics

Complete metrics for a generation session:

```python
class SessionMetrics(BaseModel):
    session_id: str
    created_at: datetime
    
    # Per-agent breakdown
    agents: Dict[str, AgentMetrics]
    
    # Totals
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_thinking_tokens: int = 0
    total_cost_usd: float = 0.0
    total_api_calls: int = 0
    
    # Pipeline timing
    pipeline_start: Optional[datetime]
    pipeline_end: Optional[datetime]
    pipeline_duration_ms: Optional[int]
```

---

## Metrics Collection

### MetricsCollector

Singleton per session that collects metrics:

```python
class MetricsCollector:
    _instances: Dict[str, MetricsCollector] = {}
    
    @classmethod
    def get_or_create(cls, session_id: str) -> MetricsCollector:
        if session_id not in cls._instances:
            cls._instances[session_id] = cls(session_id)
        return cls._instances[session_id]
    
    def record(
        self,
        agent_name: str,
        usage: TokenUsage,
        duration_ms: int = 0,
    ):
        """Record token usage for an agent."""
        self._metrics.record_usage(agent_name, usage, duration_ms)
    
    def start_pipeline(self):
        self._metrics.pipeline_start = datetime.utcnow()
    
    def end_pipeline(self):
        self._metrics.pipeline_end = datetime.utcnow()
```

### Recording Usage

Usage is recorded after each agent call:

```python
# In SlideGenerationFlow
async def _run_planner(self):
    start = time.time()
    
    # Run agent
    crew = Crew(agents=[planner], tasks=[task])
    result = crew.kickoff()
    
    duration_ms = int((time.time() - start) * 1000)
    
    # Extract usage from response
    usage = extract_usage_from_response(result, model="gemini-3-pro")
    
    # Record metrics
    self.metrics.record("planner", usage, duration_ms)
```

### Extracting Usage from Gemini Response

```python
def extract_usage_from_response(response: Any, model: str = "") -> TokenUsage:
    usage = TokenUsage(model=model)
    
    if hasattr(response, 'usage_metadata'):
        metadata = response.usage_metadata
        usage.input_tokens = getattr(metadata, 'prompt_token_count', 0)
        usage.output_tokens = getattr(metadata, 'candidates_token_count', 0)
        usage.thinking_tokens = getattr(metadata, 'thoughts_token_count', 0)
    
    elif isinstance(response, dict) and 'usage_metadata' in response:
        m = response['usage_metadata']
        usage.input_tokens = m.get('prompt_token_count', 0)
        usage.output_tokens = m.get('candidates_token_count', 0)
        usage.thinking_tokens = m.get('thoughts_token_count', 0)
    
    return usage
```

---

## API Endpoints

### GET `/api/generation/metrics/{session_id}`

Full metrics breakdown:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2025-12-21T20:30:00Z",
  "totals": {
    "input_tokens": 45000,
    "output_tokens": 28000,
    "thinking_tokens": 8500,
    "total_tokens": 81500,
    "cost_usd": 0.254,
    "api_calls": 12,
    "pipeline_duration_ms": 45230
  },
  "agents": {
    "clarifier": {
      "agent_name": "clarifier",
      "calls": 3,
      "input_tokens": 8000,
      "output_tokens": 4500,
      "thinking_tokens": 1200,
      "total_tokens": 13700,
      "cost_usd": 0.0243,
      "avg_duration_ms": 1523.5,
      "call_history": [
        {
          "input_tokens": 2500,
          "output_tokens": 1500,
          "thinking_tokens": 400,
          "model": "gemini-3-flash",
          "cost_usd": 0.0076,
          "timestamp": "2025-12-21T20:30:05Z"
        }
        // ... last 10 calls
      ]
    },
    "planner": { /* ... */ },
    "refiner": { /* ... */ },
    "generator": { /* ... */ },
    "visual_qa": { /* ... */ }
  }
}
```

### GET `/api/generation/metrics/{session_id}/summary`

Concise summary for UI:

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "input_tokens": 45000,
  "output_tokens": 28000,
  "thinking_tokens": 8500,
  "total_tokens": 81500,
  "cost_usd": 0.254,
  "api_calls": 12,
  "status": "completed"
}
```

---

## Frontend Integration

### Displaying Metrics in Testing Ground

```tsx
// components/playground/metrics-panel.tsx

interface MetricsSummary {
  input_tokens: number;
  output_tokens: number;
  thinking_tokens: number;
  total_tokens: number;
  cost_usd: number;
  api_calls: number;
}

export function MetricsPanel({ sessionId }: { sessionId: string }) {
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  
  useEffect(() => {
    const fetchMetrics = async () => {
      const res = await fetch(`/api/generation/metrics/${sessionId}/summary`);
      const data = await res.json();
      setMetrics(data);
    };
    
    // Poll every 2 seconds during generation
    const interval = setInterval(fetchMetrics, 2000);
    return () => clearInterval(interval);
  }, [sessionId]);
  
  if (!metrics) return null;
  
  return (
    <div className="metrics-panel">
      <div className="metric">
        <span className="label">Tokens</span>
        <span className="value">{metrics.total_tokens.toLocaleString()}</span>
      </div>
      <div className="metric">
        <span className="label">Cost</span>
        <span className="value">${metrics.cost_usd.toFixed(4)}</span>
      </div>
      <div className="metric">
        <span className="label">API Calls</span>
        <span className="value">{metrics.api_calls}</span>
      </div>
    </div>
  );
}
```

### Detailed Agent Breakdown

```tsx
// components/playground/agent-metrics.tsx

interface AgentMetrics {
  agent_name: string;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  thinking_tokens: number;
  cost_usd: number;
  avg_duration_ms: number;
}

export function AgentMetricsTable({ sessionId }: { sessionId: string }) {
  const [metrics, setMetrics] = useState<Record<string, AgentMetrics>>({});
  
  useEffect(() => {
    fetch(`/api/generation/metrics/${sessionId}`)
      .then(res => res.json())
      .then(data => setMetrics(data.agents || {}));
  }, [sessionId]);
  
  return (
    <table className="agent-metrics-table">
      <thead>
        <tr>
          <th>Agent</th>
          <th>Calls</th>
          <th>Input</th>
          <th>Output</th>
          <th>Thinking</th>
          <th>Cost</th>
          <th>Avg Time</th>
        </tr>
      </thead>
      <tbody>
        {Object.values(metrics).map(agent => (
          <tr key={agent.agent_name}>
            <td>{agent.agent_name}</td>
            <td>{agent.calls}</td>
            <td>{agent.input_tokens.toLocaleString()}</td>
            <td>{agent.output_tokens.toLocaleString()}</td>
            <td>{agent.thinking_tokens.toLocaleString()}</td>
            <td>${agent.cost_usd.toFixed(4)}</td>
            <td>{agent.avg_duration_ms.toFixed(0)}ms</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

---

## Cost Optimization

### Tips to Reduce Costs

1. **Use Flash where possible**
   - Flash is 4x cheaper than Pro for input
   - Only use Pro for complex reasoning

2. **Minimize context**
   - Don't send full history every call
   - Summarize previous outputs

3. **Cache common prompts**
   - System prompts don't change
   - Use Gemini's context caching

4. **Batch operations**
   - Generate multiple slides per call
   - Combine related requests

5. **Early exit conditions**
   - Stop clarification when complete
   - Skip optional stages

### Monitoring High-Cost Sessions

```python
# Check if session exceeds cost threshold
def check_cost_threshold(session_id: str, threshold: float = 1.0) -> bool:
    collector = MetricsCollector.get(session_id)
    if collector:
        return collector.get_metrics().total_cost_usd > threshold
    return False

# In flow
if check_cost_threshold(self.state.session_id, threshold=0.50):
    logger.warning(f"Session {self.state.session_id} exceeded $0.50")
    await self.emitter.emit("warning", {"message": "High token usage detected"})
```

### Model Selection by Task

| Task | Recommended Model | Reasoning |
|------|-------------------|-----------|
| Simple Q&A | Flash | Fast, cheap |
| Content generation | Pro | Better quality |
| Template selection | Flash | Pattern matching |
| Error analysis | Pro | Requires reasoning |
| Citation formatting | Flash | Structured output |
