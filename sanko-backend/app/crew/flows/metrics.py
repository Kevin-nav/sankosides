"""
Token Usage Metrics

Tracks token usage (input, thinking, output) across all agents
for cost monitoring and frontend display in the testing ground.

Pricing based on Gemini 3 API pricing (December 2025).
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# =============================================================================
# Pricing Constants (per 1M tokens) - December 2025
# =============================================================================

class GeminiPricing(str, Enum):
    """Gemini model pricing tiers."""
    FLASH_INPUT = "flash_input"
    FLASH_OUTPUT = "flash_output"
    FLASH_AUDIO_INPUT = "flash_audio_input"
    PRO_INPUT = "pro_input"
    PRO_OUTPUT = "pro_output"
    PRO_LONG_INPUT = "pro_long_input"  # >200K context
    PRO_LONG_OUTPUT = "pro_long_output"


# Gemini 3 Pricing in USD per 1M tokens (December 2025)
# Source: Google AI pricing page
PRICING: Dict[str, float] = {
    # Gemini 3 Flash 
    "flash_input": 0.50,       # $0.50 per 1M input tokens
    "flash_output": 3.00,      # $3.00 per 1M output tokens
    "flash_audio_input": 1.00, # $1.00 per 1M audio input tokens
    
    # Gemini 3 Pro (≤200K context)
    "pro_input": 2.00,         # $2.00 per 1M input tokens
    "pro_output": 12.00,       # $12.00 per 1M output tokens
    
    # Gemini 3 Pro (>200K context)
    "pro_long_input": 4.00,    # $4.00 per 1M input tokens
    "pro_long_output": 18.00,  # $18.00 per 1M output tokens
}

# Model to pricing tier mapping - Gemini 3 models
MODEL_TO_TIER: Dict[str, str] = {
    # Gemini 3 Flash variants
    "gemini-3-flash": "flash",
    "gemini-3-flash-preview": "flash",
    "gemini-3-flash-preview-05-20": "flash",
    "models/gemini-3-flash": "flash",
    
    # Gemini 3 Pro variants
    "gemini-3-pro": "pro",
    "gemini-3-pro-preview": "pro",
    "models/gemini-3-pro": "pro",
    
    # Legacy Gemini 2.x (fallback)
    "gemini-2.0-flash": "flash",
    "gemini-2.0-flash-exp": "flash",
    "gemini-2.5-flash-preview-05-20": "flash",
    "gemini-2.5-pro-preview-06-05": "pro",
}


# =============================================================================
# Token Usage Models
# =============================================================================

class TokenUsage(BaseModel):
    """Token usage for a single API call."""
    input_tokens: int = Field(default=0, description="Input/prompt tokens")
    output_tokens: int = Field(default=0, description="Output/completion tokens")
    thinking_tokens: int = Field(default=0, description="Thinking/reasoning tokens")
    
    # Metadata
    model: str = Field(default="", description="Model used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens + self.thinking_tokens
    
    def calculate_cost(self, long_context: bool = False) -> float:
        """
        Calculate cost in USD.
        
        Args:
            long_context: If True and using Pro, use >200K context pricing
        """
        tier = MODEL_TO_TIER.get(self.model, "flash")
        
        # Determine pricing keys based on tier and context length
        if tier == "pro" and long_context:
            input_key = "pro_long_input"
            output_key = "pro_long_output"
        else:
            input_key = f"{tier}_input"
            output_key = f"{tier}_output"
        
        input_cost = (self.input_tokens / 1_000_000) * PRICING[input_key]
        # Thinking tokens are billed as output tokens in Gemini 3
        output_cost = (self.output_tokens / 1_000_000) * PRICING[output_key]
        thinking_cost = (self.thinking_tokens / 1_000_000) * PRICING[output_key]
        
        return input_cost + output_cost + thinking_cost
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "thinking_tokens": self.thinking_tokens,
            "total_tokens": self.total_tokens,
            "model": self.model,
            "cost_usd": round(self.calculate_cost(), 6),
            "timestamp": self.timestamp.isoformat(),
        }


class AgentMetrics(BaseModel):
    """Aggregated metrics for a single agent."""
    agent_name: str
    calls: int = Field(default=0, description="Number of API calls")
    total_input_tokens: int = Field(default=0)
    total_output_tokens: int = Field(default=0)
    total_thinking_tokens: int = Field(default=0)
    total_cost_usd: float = Field(default=0.0)
    
    # Timing
    total_duration_ms: int = Field(default=0)
    avg_duration_ms: float = Field(default=0.0)
    
    # Per-call history (optional, for detailed view)
    call_history: List[TokenUsage] = Field(default_factory=list)
    
    def add_usage(self, usage: TokenUsage, duration_ms: int = 0):
        """Add a new usage record."""
        self.calls += 1
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_thinking_tokens += usage.thinking_tokens
        self.total_cost_usd += usage.calculate_cost()
        self.total_duration_ms += duration_ms
        self.avg_duration_ms = self.total_duration_ms / self.calls
        self.call_history.append(usage)
    
    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens + self.total_thinking_tokens
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_name": self.agent_name,
            "calls": self.calls,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "thinking_tokens": self.total_thinking_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.total_cost_usd, 6),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "call_history": [u.to_dict() for u in self.call_history[-10:]],  # Last 10 calls
        }


class SessionMetrics(BaseModel):
    """Complete metrics for a generation session."""
    session_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Per-agent metrics
    agents: Dict[str, AgentMetrics] = Field(default_factory=dict)
    
    # Aggregated totals
    total_input_tokens: int = Field(default=0)
    total_output_tokens: int = Field(default=0)
    total_thinking_tokens: int = Field(default=0)
    total_cost_usd: float = Field(default=0.0)
    total_api_calls: int = Field(default=0)
    
    # Pipeline timing
    pipeline_start: Optional[datetime] = None
    pipeline_end: Optional[datetime] = None
    
    def get_agent(self, agent_name: str) -> AgentMetrics:
        """Get or create agent metrics."""
        if agent_name not in self.agents:
            self.agents[agent_name] = AgentMetrics(agent_name=agent_name)
        return self.agents[agent_name]
    
    def record_usage(
        self,
        agent_name: str,
        usage: TokenUsage,
        duration_ms: int = 0,
    ):
        """Record token usage for an agent."""
        agent = self.get_agent(agent_name)
        agent.add_usage(usage, duration_ms)
        
        # Update totals
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.total_thinking_tokens += usage.thinking_tokens
        self.total_cost_usd += usage.calculate_cost()
        self.total_api_calls += 1
    
    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens + self.total_thinking_tokens
    
    @property
    def pipeline_duration_ms(self) -> Optional[int]:
        if self.pipeline_start and self.pipeline_end:
            return int((self.pipeline_end - self.pipeline_start).total_seconds() * 1000)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "totals": {
                "input_tokens": self.total_input_tokens,
                "output_tokens": self.total_output_tokens,
                "thinking_tokens": self.total_thinking_tokens,
                "total_tokens": self.total_tokens,
                "cost_usd": round(self.total_cost_usd, 6),
                "api_calls": self.total_api_calls,
                "pipeline_duration_ms": self.pipeline_duration_ms,
            },
            "agents": {name: agent.to_dict() for name, agent in self.agents.items()},
        }


# =============================================================================
# Metrics Collector (Singleton per session)
# =============================================================================

class MetricsCollector:
    """
    Collects and aggregates metrics across a generation session.
    
    Usage:
        collector = MetricsCollector(session_id)
        collector.record("clarifier", TokenUsage(...), duration_ms=1500)
        metrics = collector.get_metrics()
    """
    
    _instances: Dict[str, "MetricsCollector"] = {}
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        self._metrics = SessionMetrics(session_id=session_id)
        MetricsCollector._instances[session_id] = self
    
    @classmethod
    def get_or_create(cls, session_id: str) -> "MetricsCollector":
        """Get existing collector or create new one."""
        if session_id not in cls._instances:
            cls._instances[session_id] = cls(session_id)
        return cls._instances[session_id]
    
    @classmethod
    def get(cls, session_id: str) -> Optional["MetricsCollector"]:
        """Get existing collector or None."""
        return cls._instances.get(session_id)
    
    def record(
        self,
        agent_name: str,
        usage: TokenUsage,
        duration_ms: int = 0,
    ):
        """Record token usage for an agent."""
        self._metrics.record_usage(agent_name, usage, duration_ms)
    
    def start_pipeline(self):
        """Mark pipeline start."""
        self._metrics.pipeline_start = datetime.utcnow()
    
    def end_pipeline(self):
        """Mark pipeline end."""
        self._metrics.pipeline_end = datetime.utcnow()
    
    def get_metrics(self) -> SessionMetrics:
        """Get current metrics."""
        return self._metrics
    
    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dict."""
        return self._metrics.to_dict()


# =============================================================================
# Helper to extract usage from Gemini response
# =============================================================================

def extract_usage_from_response(response: Any, model: str = "") -> TokenUsage:
    """
    Extract token usage from a Gemini API response.
    
    Works with both generate_content and streaming responses.
    """
    usage = TokenUsage(model=model)
    
    if hasattr(response, 'usage_metadata'):
        metadata = response.usage_metadata
        usage.input_tokens = getattr(metadata, 'prompt_token_count', 0) or 0
        usage.output_tokens = getattr(metadata, 'candidates_token_count', 0) or 0
        usage.thinking_tokens = getattr(metadata, 'thoughts_token_count', 0) or 0
    
    elif hasattr(response, 'usage'):
        # CrewAI-style usage
        u = response.usage
        usage.input_tokens = getattr(u, 'prompt_tokens', 0) or getattr(u, 'input_tokens', 0) or 0
        usage.output_tokens = getattr(u, 'completion_tokens', 0) or getattr(u, 'output_tokens', 0) or 0
        usage.thinking_tokens = getattr(u, 'thinking_tokens', 0) or 0
    
    elif isinstance(response, dict):
        # Dict-style response
        if 'usage_metadata' in response:
            m = response['usage_metadata']
            usage.input_tokens = m.get('prompt_token_count', 0)
            usage.output_tokens = m.get('candidates_token_count', 0)
            usage.thinking_tokens = m.get('thoughts_token_count', 0)
        elif 'usage' in response:
            u = response['usage']
            usage.input_tokens = u.get('input_tokens', u.get('prompt_tokens', 0))
            usage.output_tokens = u.get('output_tokens', u.get('completion_tokens', 0))
            usage.thinking_tokens = u.get('thinking_tokens', 0)
    
    return usage
