"""
Main test runner for Gemini PDF synthesis testing.

Usage:
    python runner.py --runs 5                     # Run all strategies 5 times each
    python runner.py --strategy baseline --runs 3 # Run only baseline 3 times
    python runner.py --pdf "Calculus 166.pdf"     # Test specific PDF
    python runner.py --list-strategies            # List available strategies

Features:
    - Graceful shutdown on Ctrl+C (saves progress)
    - Incremental saves after each run
    - Live activity logging
    - Resume capability from partial runs
"""

import os
import sys
import signal
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager

# Ensure we can import from the test_synthesis module
sys.path.insert(0, str(Path(__file__).parent))

from metrics import MetricsCollector, SynthesisRunMetrics, ActivityLog
from strategies import STRATEGIES, get_strategy
from config import get_api_key, print_config_summary, DEFAULT_MODEL, GEMINI_MODELS


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# Default test PDFs directory
DEFAULT_PDF_DIR = Path(__file__).parent.parent.parent / "pdfs_for_testing"


class GracefulShutdown:
    """Context manager for handling graceful shutdown on SIGINT/SIGTERM."""
    
    def __init__(self):
        self.shutdown_requested = False
        self._original_sigint = None
        self._original_sigterm = None
    
    def __enter__(self):
        self._original_sigint = signal.signal(signal.SIGINT, self._handle_signal)
        self._original_sigterm = signal.signal(signal.SIGTERM, self._handle_signal)
        return self
    
    def __exit__(self, *args):
        signal.signal(signal.SIGINT, self._original_sigint)
        signal.signal(signal.SIGTERM, self._original_sigterm)
    
    def _handle_signal(self, signum, frame):
        if self.shutdown_requested:
            logger.warning("Force shutdown requested. Exiting immediately.")
            sys.exit(1)
        
        logger.warning("Shutdown requested. Finishing current run and saving progress...")
        logger.warning("Press Ctrl+C again to force quit.")
        self.shutdown_requested = True
    
    def check(self) -> bool:
        """Check if shutdown was requested. Returns True if should continue."""
        return not self.shutdown_requested


def get_test_pdfs(pdf_dir: Path, specific_pdf: Optional[str] = None) -> List[Path]:
    """Get list of PDF files to test."""
    if not pdf_dir.exists():
        logger.error(f"PDF directory not found: {pdf_dir}")
        return []
    
    pdfs = list(pdf_dir.glob("*.pdf"))
    
    if specific_pdf:
        pdfs = [p for p in pdfs if specific_pdf.lower() in p.name.lower()]
        if not pdfs:
            logger.warning(f"No PDFs matching '{specific_pdf}' found")
    
    return sorted(pdfs, key=lambda p: p.stat().st_size)


def run_single_test(
    pdf_path: Path,
    strategy_name: str,
    api_key: str,
    collector: MetricsCollector,
) -> SynthesisRunMetrics:
    """Run a single synthesis test."""
    strategy = get_strategy(strategy_name, api_key)
    
    # Create metrics for this run
    metrics = collector.create_run(
        pdf_name=pdf_path.name,
        pdf_size=pdf_path.stat().st_size,
        strategy=strategy_name,
    )
    
    # Log activity start
    collector.log_activity(
        run_id=metrics.run_id,
        event="started",
        details=f"PDF: {pdf_path.name}, Strategy: {strategy_name}",
    )
    
    logger.info(f"[{metrics.run_id}] {pdf_path.name} | {strategy_name}")
    
    try:
        result = strategy.synthesize(pdf_path, metrics)
        
        if result.success:
            logger.info(
                f"    [OK] {metrics.quality.sections_count} sections, "
                f"{metrics.performance.total_time_ms:.0f}ms"
            )
            collector.log_activity(
                run_id=metrics.run_id,
                event="completed",
                details=f"Sections: {metrics.quality.sections_count}, Time: {metrics.performance.total_time_ms:.0f}ms",
            )
        else:
            logger.warning(
                f"    [FAIL] {result.error_type.value}: {result.error_message[:80]}..."
            )
            collector.log_activity(
                run_id=metrics.run_id,
                event="failed",
                details=f"{result.error_type.value}: {result.error_message[:100]}",
            )
            
    except Exception as e:
        logger.error(f"    [ERROR] {str(e)[:80]}...")
        metrics.failure.success = False
        metrics.failure.error_message = str(e)
        collector.log_activity(
            run_id=metrics.run_id,
            event="error",
            details=str(e)[:200],
        )
    
    # Record and save immediately (incremental save)
    collector.record_run(metrics)
    collector.save_incremental()
    
    return metrics


def run_test_suite(
    pdf_dir: Path,
    strategies: List[str],
    runs_per_combo: int,
    api_key: str,
    specific_pdf: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Run the full test suite with graceful shutdown support."""
    
    pdfs = get_test_pdfs(pdf_dir, specific_pdf)
    if not pdfs:
        logger.error("No PDFs to test!")
        sys.exit(1)
    
    # Setup output directory
    if output_dir is None:
        output_dir = Path(__file__).parent / "results"
    
    run_name = datetime.now().strftime("run_%Y-%m-%d_%H-%M-%S")
    collector = MetricsCollector(output_dir, run_name)
    
    # Calculate totals
    total_tests = len(pdfs) * len(strategies) * runs_per_combo
    
    # Header
    logger.info("=" * 60)
    logger.info("GEMINI PDF SYNTHESIS TEST SUITE")
    logger.info("=" * 60)
    logger.info(f"PDFs:       {len(pdfs)} files")
    logger.info(f"Strategies: {len(strategies)}")
    logger.info(f"Runs each:  {runs_per_combo}")
    logger.info(f"Total runs: {total_tests}")
    logger.info(f"Output:     {collector.run_dir}")
    logger.info("=" * 60)
    
    # List PDFs
    logger.info("Test PDFs:")
    for pdf in pdfs:
        size_mb = pdf.stat().st_size / (1024 * 1024)
        logger.info(f"  - {pdf.name} ({size_mb:.1f} MB)")
    
    logger.info("Strategies:")
    for s in strategies:
        logger.info(f"  - {s}")
    
    logger.info("-" * 60)
    
    # Run tests with graceful shutdown
    current_test = 0
    completed_runs = 0
    
    with GracefulShutdown() as shutdown:
        for run_num in range(runs_per_combo):
            if not shutdown.check():
                break
                
            logger.info(f"=== RUN {run_num + 1}/{runs_per_combo} ===")
            
            for pdf_path in pdfs:
                if not shutdown.check():
                    break
                
                for strategy_name in strategies:
                    if not shutdown.check():
                        break
                    
                    current_test += 1
                    progress = current_test / total_tests * 100
                    logger.info(f"[{progress:5.1f}%] Starting test {current_test}/{total_tests}")
                    
                    run_single_test(pdf_path, strategy_name, api_key, collector)
                    completed_runs += 1
        
        # Check if we were interrupted
        if shutdown.shutdown_requested:
            logger.warning(f"Interrupted. Completed {completed_runs}/{total_tests} runs.")
    
    # Final save and summary
    logger.info("=" * 60)
    logger.info("SAVING FINAL RESULTS...")
    results_dir = collector.save_results()
    
    # Print summary
    summary = collector.get_summary()
    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total runs:    {summary['total_runs']}")
    logger.info(f"Success rate:  {summary['overall']['success_rate']:.1f}%")
    logger.info(f"Failures:      {summary['overall']['failures']}")
    
    if summary['overall'].get('error_types'):
        logger.info("Error breakdown:")
        for error_type, count in summary['overall']['error_types'].items():
            logger.info(f"  {error_type}: {count}")
    
    logger.info("By Strategy:")
    for strategy, stats in summary.get('by_strategy', {}).items():
        logger.info(f"  {strategy}: {stats['success_rate']:.1f}% success, avg {stats['avg_time_ms']:.0f}ms")
    
    logger.info("By PDF:")
    for pdf, stats in summary.get('by_pdf', {}).items():
        logger.info(f"  {pdf[:30]}: {stats['success_rate']:.1f}% success")
    
    logger.info(f"Results saved to: {results_dir}")
    logger.info("=" * 60)
    
    return results_dir


def main():
    parser = argparse.ArgumentParser(
        description="Gemini PDF Synthesis Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python runner.py --runs 3                    Run all strategies 3 times each
  python runner.py --strategy baseline         Run only baseline strategy
  python runner.py --pdf "Calculus"            Test PDFs matching "Calculus"
  python runner.py --list-strategies           Show available strategies
  python runner.py --list-models               Show available Gemini models
        """
    )
    parser.add_argument("--runs", type=int, default=3, help="Number of runs per PDF/strategy combo")
    parser.add_argument("--strategy", type=str, help="Specific strategy to test (default: all)")
    parser.add_argument("--pdf", type=str, help="Specific PDF to test (partial match)")
    parser.add_argument("--pdf-dir", type=str, help="Directory containing test PDFs")
    parser.add_argument("--output-dir", type=str, help="Output directory for results")
    parser.add_argument("--list-strategies", action="store_true", help="List available strategies")
    parser.add_argument("--list-models", action="store_true", help="List available Gemini models")
    parser.add_argument("--api-key", type=str, help="Gemini API key (or set GEMINI_API_KEY env)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if args.list_strategies:
        print("Available strategies:")
        for name in STRATEGIES.keys():
            print(f"  - {name}")
        return
    
    if args.list_models:
        print("Available Gemini models:")
        for model, desc in GEMINI_MODELS.items():
            marker = " *" if model == DEFAULT_MODEL else ""
            print(f"  {model}: {desc}{marker}")
        print("\n  * = default model")
        return
    
    # Get API key from config
    api_key = args.api_key
    if not api_key:
        try:
            api_key = get_api_key()
        except ValueError as e:
            logger.error(str(e))
            sys.exit(1)
    
    # Show configuration summary
    print_config_summary()
    
    # Determine strategies to test
    if args.strategy:
        if args.strategy not in STRATEGIES:
            logger.error(f"Unknown strategy '{args.strategy}'")
            logger.error(f"Available: {list(STRATEGIES.keys())}")
            sys.exit(1)
        strategies = [args.strategy]
    else:
        strategies = list(STRATEGIES.keys())
    
    # PDF directory
    pdf_dir = Path(args.pdf_dir) if args.pdf_dir else DEFAULT_PDF_DIR
    
    # Output directory
    output_dir = Path(args.output_dir) if args.output_dir else None
    
    # Run tests
    run_test_suite(
        pdf_dir=pdf_dir,
        strategies=strategies,
        runs_per_combo=args.runs,
        api_key=api_key,
        specific_pdf=args.pdf,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    main()
