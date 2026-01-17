"""
Metrics collection and tracking for Gemini PDF synthesis testing.
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum


class ErrorType(str, Enum):
    """Classification of synthesis errors."""
    SUCCESS = "success"
    JSON_PARSE_ERROR = "json_parse_error"
    JSON_TRUNCATED = "json_truncated"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    VALIDATION_ERROR = "validation_error"
    FILE_ERROR = "file_error"
    UNKNOWN = "unknown"


@dataclass
class PerformanceMetrics:
    """Timing metrics for a synthesis run."""
    total_time_ms: float = 0.0
    api_latency_ms: float = 0.0
    json_parse_time_ms: float = 0.0
    validation_time_ms: float = 0.0
    chunk_times_ms: List[float] = field(default_factory=list)  # For chunked strategies


@dataclass
class QualityMetrics:
    """Content quality metrics."""
    sections_count: int = 0
    total_content_chars: int = 0
    avg_section_chars: float = 0.0
    min_section_chars: int = 0
    max_section_chars: int = 0
    sections_with_visuals: int = 0
    sections_with_latex: int = 0
    sections_with_page_range: int = 0
    empty_sections: int = 0
    # Cross-chunk analysis
    potential_split_sections: int = 0  # Sections that might span chunks
    merged_sections: int = 0  # Sections merged from multiple chunks


@dataclass
class ResponseMetrics:
    """Raw response analysis."""
    raw_response_chars: int = 0
    valid_json: bool = False
    json_parse_error: Optional[str] = None
    response_tokens_estimate: int = 0  # chars / 4 approximation
    appears_truncated: bool = False
    truncation_indicators: List[str] = field(default_factory=list)


@dataclass
class FailureMetrics:
    """Failure tracking."""
    success: bool = True
    error_type: ErrorType = ErrorType.SUCCESS
    error_message: Optional[str] = None
    retry_count: int = 0
    failed_at_stage: Optional[str] = None  # "api_call", "json_parse", "validation"


@dataclass
class ActivityLog:
    """Single activity log entry for real-time visibility."""
    timestamp: str
    run_id: str
    event: str  # "started", "completed", "failed", "error"
    details: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "run_id": self.run_id,
            "event": self.event,
            "details": self.details,
        }


@dataclass
class SynthesisRunMetrics:
    """Complete metrics for a single synthesis run."""
    # Identification
    run_id: str = ""
    pdf_name: str = ""
    pdf_size_bytes: int = 0
    strategy_name: str = ""
    timestamp: str = ""
    
    # Sub-metrics
    performance: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    quality: QualityMetrics = field(default_factory=QualityMetrics)
    response: ResponseMetrics = field(default_factory=ResponseMetrics)
    failure: FailureMetrics = field(default_factory=FailureMetrics)
    
    # Strategy-specific
    strategy_params: Dict[str, Any] = field(default_factory=dict)
    chunks_processed: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "run_id": self.run_id,
            "pdf_name": self.pdf_name,
            "pdf_size_bytes": self.pdf_size_bytes,
            "strategy_name": self.strategy_name,
            "timestamp": self.timestamp,
            "performance": asdict(self.performance),
            "quality": asdict(self.quality),
            "response": asdict(self.response),
            "failure": {
                **asdict(self.failure),
                "error_type": self.failure.error_type.value
            },
            "strategy_params": self.strategy_params,
            "chunks_processed": self.chunks_processed,
        }


class MetricsTimer:
    """Context manager for timing operations."""
    
    def __init__(self):
        self.start_time: float = 0
        self.end_time: float = 0
        self.elapsed_ms: float = 0
    
    def __enter__(self):
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        self.elapsed_ms = (self.end_time - self.start_time) * 1000


class MetricsCollector:
    """Collects and aggregates metrics across multiple runs with incremental saves."""
    
    def __init__(self, results_dir: Path, run_name: Optional[str] = None):
        self.results_dir = results_dir
        self.results_dir.mkdir(parents=True, exist_ok=True)
        
        # Create run-specific directory
        if run_name is None:
            run_name = datetime.now().strftime("run_%Y-%m-%d_%H-%M-%S")
        self.run_name = run_name
        self.run_dir = self.results_dir / run_name
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        self.runs: List[SynthesisRunMetrics] = []
        self.activities: List[ActivityLog] = []
        self.run_counter = 0
        
        # Files for incremental saves
        self._runs_file = self.run_dir / "runs.json"
        self._activity_file = self.run_dir / "activity.json"
        self._summary_file = self.run_dir / "summary.json"
        self._status_file = self.run_dir / "status.json"
        
        # Initialize status
        self._update_status("running")
    
    def _update_status(self, status: str, details: Optional[str] = None):
        """Update the status file for dashboard visibility."""
        status_data = {
            "status": status,
            "last_updated": datetime.now().isoformat(),
            "total_runs": len(self.runs),
            "completed_runs": len([r for r in self.runs if r.failure.success]),
            "failed_runs": len([r for r in self.runs if not r.failure.success]),
            "details": details,
        }
        with open(self._status_file, "w") as f:
            json.dump(status_data, f, indent=2)
    
    def create_run(self, pdf_name: str, pdf_size: int, strategy: str) -> SynthesisRunMetrics:
        """Create a new run with initialized metrics."""
        self.run_counter += 1
        return SynthesisRunMetrics(
            run_id=f"run_{self.run_counter:04d}",
            pdf_name=pdf_name,
            pdf_size_bytes=pdf_size,
            strategy_name=strategy,
            timestamp=datetime.now().isoformat(),
        )
    
    def record_run(self, metrics: SynthesisRunMetrics):
        """Record a completed run."""
        self.runs.append(metrics)
    
    def log_activity(self, run_id: str, event: str, details: str):
        """Log an activity for real-time visibility."""
        activity = ActivityLog(
            timestamp=datetime.now().isoformat(),
            run_id=run_id,
            event=event,
            details=details,
        )
        self.activities.append(activity)
        
        # Append to activity file immediately
        self._append_activity(activity)
    
    def _append_activity(self, activity: ActivityLog):
        """Append a single activity to the activity log file."""
        activities = []
        if self._activity_file.exists():
            try:
                with open(self._activity_file) as f:
                    activities = json.load(f)
            except (json.JSONDecodeError, IOError):
                activities = []
        
        activities.append(activity.to_dict())
        
        with open(self._activity_file, "w") as f:
            json.dump(activities, f, indent=2)
    
    def save_incremental(self):
        """Save current state incrementally (called after each run)."""
        # Save runs
        with open(self._runs_file, "w") as f:
            json.dump([r.to_dict() for r in self.runs], f, indent=2)
        
        # Update summary
        with open(self._summary_file, "w") as f:
            json.dump(self.get_summary(), f, indent=2)
        
        # Update status
        self._update_status("running", f"Completed {len(self.runs)} runs")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get aggregated summary statistics."""
        if not self.runs:
            return {"total_runs": 0}
        
        by_strategy: Dict[str, List[SynthesisRunMetrics]] = {}
        by_pdf: Dict[str, List[SynthesisRunMetrics]] = {}
        
        for run in self.runs:
            by_strategy.setdefault(run.strategy_name, []).append(run)
            by_pdf.setdefault(run.pdf_name, []).append(run)
        
        def calc_stats(runs: List[SynthesisRunMetrics]) -> Dict[str, Any]:
            successes = [r for r in runs if r.failure.success]
            failures = [r for r in runs if not r.failure.success]
            return {
                "total": len(runs),
                "successes": len(successes),
                "failures": len(failures),
                "success_rate": len(successes) / len(runs) * 100 if runs else 0,
                "avg_time_ms": sum(r.performance.total_time_ms for r in successes) / len(successes) if successes else 0,
                "avg_sections": sum(r.quality.sections_count for r in successes) / len(successes) if successes else 0,
                "error_types": {et.value: len([r for r in failures if r.failure.error_type == et]) 
                               for et in ErrorType if any(r.failure.error_type == et for r in failures)},
            }
        
        return {
            "run_name": self.run_name,
            "total_runs": len(self.runs),
            "last_updated": datetime.now().isoformat(),
            "overall": calc_stats(self.runs),
            "by_strategy": {name: calc_stats(runs) for name, runs in by_strategy.items()},
            "by_pdf": {name: calc_stats(runs) for name, runs in by_pdf.items()},
        }
    
    def save_results(self) -> Path:
        """Save final results and mark as complete."""
        # Final save
        self.save_incremental()
        
        # Update status to complete
        self._update_status("complete", f"Finished with {len(self.runs)} runs")
        
        return self.run_dir


def detect_truncation(response_text: str) -> tuple[bool, List[str]]:
    """
    Detect if a JSON response appears to be truncated.
    
    Returns:
        (is_truncated, list of indicators found)
    """
    indicators = []
    
    # Check for unclosed braces/brackets
    open_braces = response_text.count("{") - response_text.count("}")
    open_brackets = response_text.count("[") - response_text.count("]")
    
    if open_braces > 0:
        indicators.append(f"unclosed_braces:{open_braces}")
    if open_brackets > 0:
        indicators.append(f"unclosed_brackets:{open_brackets}")
    
    # Check for incomplete strings
    if response_text.rstrip().endswith(","):
        indicators.append("ends_with_comma")
    if response_text.count('"') % 2 != 0:
        indicators.append("unclosed_string")
    
    # Check for common truncation patterns
    truncation_patterns = [
        "...",
        "[truncated]",
        "...",
    ]
    for pattern in truncation_patterns:
        if pattern in response_text[-100:]:
            indicators.append(f"pattern:{pattern}")
    
    return len(indicators) > 0, indicators


def analyze_latex_content(content: str) -> bool:
    """Check if content contains LaTeX."""
    latex_indicators = ["$", "\\frac", "\\sum", "\\int", "\\alpha", "\\beta", "\\gamma"]
    return any(ind in content for ind in latex_indicators)


def repair_truncated_json(text: str) -> tuple[Optional[Dict], bool, str]:
    """
    Attempt to repair truncated JSON.
    
    Returns:
        (parsed_dict, was_repaired, repair_notes)
    """
    import re
    
    # First try normal parsing
    try:
        return json.loads(text), False, "valid_json"
    except json.JSONDecodeError:
        pass
    
    # Track repair actions
    repairs = []
    repaired_text = text
    
    # Fix invalid escape sequences (e.g., \n in the middle of strings that should be \\n)
    # This handles cases like "Invalid \escape" error
    def fix_escapes(match):
        s = match.group(0)
        # Replace problematic escapes
        s = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', s)
        return s
    
    # Fix strings with invalid escapes
    repaired_text = re.sub(r'"[^"]*"', fix_escapes, repaired_text)
    if repaired_text != text:
        repairs.append("fixed_escapes")
    
    # Try parsing after escape fix
    try:
        return json.loads(repaired_text), True, ",".join(repairs) if repairs else "escape_fix"
    except json.JSONDecodeError:
        pass
    
    # Count open/close brackets
    open_braces = repaired_text.count("{") - repaired_text.count("}")
    open_brackets = repaired_text.count("[") - repaired_text.count("]")
    
    # Find the last complete section by looking for pattern: }]
    # This helps salvage partial responses
    last_complete = repaired_text.rfind("},")
    if last_complete > 0:
        # Try to close from there
        candidate = repaired_text[:last_complete + 1] + "]}"
        try:
            result = json.loads(candidate)
            repairs.append(f"truncated_at_char_{last_complete}")
            return result, True, ",".join(repairs)
        except json.JSONDecodeError:
            pass
    
    # Try closing unclosed strings
    if repaired_text.count('"') % 2 != 0:
        repaired_text = repaired_text + '"'
        repairs.append("closed_string")
    
    # Close brackets/braces
    if open_brackets > 0:
        repaired_text = repaired_text + "]" * open_brackets
        repairs.append(f"closed_{open_brackets}_brackets")
    
    if open_braces > 0:
        repaired_text = repaired_text + "}" * open_braces
        repairs.append(f"closed_{open_braces}_braces")
    
    # Remove trailing comma before closing
    repaired_text = re.sub(r',\s*([}\]])', r'\1', repaired_text)
    
    # Final attempt
    try:
        return json.loads(repaired_text), True, ",".join(repairs)
    except json.JSONDecodeError as e:
        return None, False, f"repair_failed:{e}"

