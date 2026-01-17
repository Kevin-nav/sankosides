"""
Streamlit dashboard for viewing synthesis test results.

Usage:
    streamlit run dashboard.py
    streamlit run dashboard.py -- --results-dir ./results/run_2024-12-27_10-00-00
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
import argparse

try:
    import streamlit as st
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    print("Dashboard requires additional packages. Install with:")
    print("  pip install streamlit pandas plotly")
    sys.exit(1)


# Page config
st.set_page_config(
    page_title="Gemini Synthesis Test Dashboard",
    page_icon=None,
    layout="wide",
)


def load_results(results_dir: Path) -> tuple[List[Dict], Dict, List[Dict], Dict]:
    """Load results from a run directory."""
    runs_file = results_dir / "runs.json"
    summary_file = results_dir / "summary.json"
    activity_file = results_dir / "activity.json"
    status_file = results_dir / "status.json"
    
    runs = []
    summary = {}
    activities = []
    status = {}
    
    if runs_file.exists():
        with open(runs_file) as f:
            runs = json.load(f)
    
    if summary_file.exists():
        with open(summary_file) as f:
            summary = json.load(f)
    
    if activity_file.exists():
        with open(activity_file) as f:
            activities = json.load(f)
    
    if status_file.exists():
        with open(status_file) as f:
            status = json.load(f)
    
    return runs, summary, activities, status


def get_available_runs(results_base: Path) -> List[Path]:
    """Get list of available test runs."""
    if not results_base.exists():
        return []
    return sorted(
        [d for d in results_base.iterdir() if d.is_dir() and (d / "runs.json").exists()],
        reverse=True
    )


def runs_to_dataframe(runs: List[Dict]) -> pd.DataFrame:
    """Convert runs to a flat DataFrame for analysis."""
    records = []
    for run in runs:
        record = {
            "run_id": run["run_id"],
            "pdf_name": run["pdf_name"],
            "pdf_size_mb": run["pdf_size_bytes"] / (1024 * 1024),
            "strategy": run["strategy_name"],
            "timestamp": run["timestamp"],
            "success": run["failure"]["success"],
            "error_type": run["failure"]["error_type"],
            "error_message": run["failure"].get("error_message", ""),
            # Performance
            "total_time_ms": run["performance"]["total_time_ms"],
            "api_latency_ms": run["performance"]["api_latency_ms"],
            "json_parse_time_ms": run["performance"]["json_parse_time_ms"],
            # Quality
            "sections_count": run["quality"]["sections_count"],
            "total_content_chars": run["quality"]["total_content_chars"],
            "avg_section_chars": run["quality"]["avg_section_chars"],
            "sections_with_latex": run["quality"]["sections_with_latex"],
            "sections_with_visuals": run["quality"]["sections_with_visuals"],
            "empty_sections": run["quality"]["empty_sections"],
            # Response
            "raw_response_chars": run["response"]["raw_response_chars"],
            "valid_json": run["response"]["valid_json"],
            "appears_truncated": run["response"]["appears_truncated"],
            # Chunks
            "chunks_processed": run.get("chunks_processed", 1),
        }
        records.append(record)
    
    return pd.DataFrame(records)


def main():
    st.title("Gemini PDF Synthesis Test Dashboard")
    
    # Sidebar - Run selection
    st.sidebar.header("Select Test Run")
    
    results_base = Path(__file__).parent / "results"
    available_runs = get_available_runs(results_base)
    
    if not available_runs:
        st.warning("No test results found. Run the test suite first:")
        st.code("python runner.py --runs 3")
        return
    
    selected_run = st.sidebar.selectbox(
        "Test Run",
        available_runs,
        format_func=lambda x: x.name,
    )
    
    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto-refresh (5s)", value=False)
    if auto_refresh:
        st.rerun()
    
    # Load data
    runs, summary, activities, status = load_results(selected_run)
    
    if not runs:
        st.info(f"No runs found in {selected_run}")
        if status:
            st.write(f"Status: {status.get('status', 'unknown')}")
        return
    
    df = runs_to_dataframe(runs)
    
    # Status banner
    if status:
        status_text = status.get("status", "unknown")
        if status_text == "running":
            st.info(f"Test suite is currently running. {status.get('details', '')}")
        elif status_text == "complete":
            st.success(f"Test suite complete. {status.get('details', '')}")
    
    # Overview metrics
    st.header("Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total = len(df)
    successes = df["success"].sum()
    failures = total - successes
    success_rate = successes / total * 100 if total > 0 else 0
    
    col1.metric("Total Runs", total)
    col2.metric("Successes", int(successes))
    col3.metric("Failures", int(failures))
    col4.metric("Success Rate", f"{success_rate:.1f}%")
    col5.metric("Avg Time", f"{df[df['success']]['total_time_ms'].mean():.0f}ms")
    
    # Activity Log (real-time visibility)
    if activities:
        st.header("Activity Log")
        with st.expander("Recent Activity", expanded=True):
            # Show last 20 activities
            recent_activities = activities[-20:][::-1]  # Reverse to show newest first
            
            activity_df = pd.DataFrame(recent_activities)
            activity_df["timestamp"] = pd.to_datetime(activity_df["timestamp"]).dt.strftime("%H:%M:%S")
            
            # Color code by event type
            def style_event(val):
                if val == "completed":
                    return "background-color: #d4edda"
                elif val == "failed":
                    return "background-color: #f8d7da"
                elif val == "error":
                    return "background-color: #f5c6cb"
                return ""
            
            styled_df = activity_df.style.applymap(style_event, subset=["event"])
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
    
    # Strategy comparison
    st.header("Strategy Comparison")
    
    strategy_stats = df.groupby("strategy").agg({
        "success": ["sum", "count"],
        "total_time_ms": "mean",
        "sections_count": "mean",
        "api_latency_ms": "mean",
    }).round(2)
    strategy_stats.columns = ["Successes", "Total", "Avg Time (ms)", "Avg Sections", "Avg API Latency (ms)"]
    strategy_stats["Success Rate"] = (strategy_stats["Successes"] / strategy_stats["Total"] * 100).round(1)
    strategy_stats = strategy_stats[["Success Rate", "Successes", "Total", "Avg Time (ms)", "Avg Sections", "Avg API Latency (ms)"]]
    
    st.dataframe(strategy_stats, use_container_width=True)
    
    # Success rate by strategy chart
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            strategy_stats.reset_index(),
            x="strategy",
            y="Success Rate",
            color="Success Rate",
            color_continuous_scale="RdYlGn",
            title="Success Rate by Strategy",
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.bar(
            strategy_stats.reset_index(),
            x="strategy",
            y="Avg Time (ms)",
            color="Avg Time (ms)",
            color_continuous_scale="Blues_r",
            title="Average Processing Time by Strategy",
        )
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    
    # PDF Analysis
    st.header("PDF Analysis")
    
    pdf_stats = df.groupby("pdf_name").agg({
        "success": ["sum", "count"],
        "pdf_size_mb": "first",
        "total_time_ms": "mean",
        "sections_count": "mean",
    }).round(2)
    pdf_stats.columns = ["Successes", "Total", "Size (MB)", "Avg Time (ms)", "Avg Sections"]
    pdf_stats["Success Rate"] = (pdf_stats["Successes"] / pdf_stats["Total"] * 100).round(1)
    pdf_stats = pdf_stats[["Size (MB)", "Success Rate", "Successes", "Total", "Avg Time (ms)", "Avg Sections"]]
    pdf_stats = pdf_stats.sort_values("Size (MB)")
    
    st.dataframe(pdf_stats, use_container_width=True)
    
    # Size vs Success Rate
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.scatter(
            pdf_stats.reset_index(),
            x="Size (MB)",
            y="Success Rate",
            size="Total",
            hover_name="pdf_name",
            title="PDF Size vs Success Rate",
            color="Success Rate",
            color_continuous_scale="RdYlGn",
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        fig = px.scatter(
            pdf_stats.reset_index(),
            x="Size (MB)",
            y="Avg Time (ms)",
            size="Total",
            hover_name="pdf_name",
            title="PDF Size vs Processing Time",
            color="Avg Time (ms)",
            color_continuous_scale="Blues",
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Error Analysis
    st.header("Error Analysis")
    
    failures_df = df[~df["success"]]
    
    if len(failures_df) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            error_counts = failures_df["error_type"].value_counts()
            fig = px.pie(
                values=error_counts.values,
                names=error_counts.index,
                title="Error Type Distribution",
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            truncation_counts = failures_df.groupby(["strategy", "appears_truncated"]).size().unstack(fill_value=0)
            if True in truncation_counts.columns:
                fig = px.bar(
                    truncation_counts.reset_index(),
                    x="strategy",
                    y=True,
                    title="Truncation Errors by Strategy",
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No truncation errors detected")
        
        # Error details table
        st.subheader("Error Details")
        error_details = failures_df[["run_id", "pdf_name", "strategy", "error_type", "error_message", "appears_truncated", "raw_response_chars"]]
        st.dataframe(error_details, use_container_width=True)
    else:
        st.success("No failures! All runs succeeded.")
    
    # Quality Metrics
    st.header("Quality Metrics")
    
    successful_df = df[df["success"]]
    
    if len(successful_df) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.box(
                successful_df,
                x="strategy",
                y="sections_count",
                title="Sections Extracted by Strategy",
                color="strategy",
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.box(
                successful_df,
                x="strategy",
                y="total_content_chars",
                title="Total Content Characters by Strategy",
                color="strategy",
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # LaTeX and Visual extraction
        col1, col2 = st.columns(2)
        
        with col1:
            latex_stats = successful_df.groupby("strategy")["sections_with_latex"].mean()
            fig = px.bar(
                latex_stats.reset_index(),
                x="strategy",
                y="sections_with_latex",
                title="Avg Sections with LaTeX by Strategy",
                color="sections_with_latex",
                color_continuous_scale="Purples",
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            visual_stats = successful_df.groupby("strategy")["sections_with_visuals"].mean()
            fig = px.bar(
                visual_stats.reset_index(),
                x="strategy",
                y="sections_with_visuals",
                title="Avg Sections with Visuals by Strategy",
                color="sections_with_visuals",
                color_continuous_scale="Oranges",
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Performance Timeline
    st.header("Performance Timeline")
    
    if len(df) > 0:
        df_sorted = df.sort_values("timestamp")
        df_sorted["run_number"] = range(1, len(df_sorted) + 1)
        
        fig = px.scatter(
            df_sorted,
            x="run_number",
            y="total_time_ms",
            color="success",
            symbol="strategy",
            hover_data=["pdf_name", "strategy", "error_type"],
            title="Processing Time Over Runs",
            labels={"run_number": "Run #", "total_time_ms": "Time (ms)"},
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Raw Data
    st.header("Raw Data")
    
    with st.expander("View All Runs"):
        st.dataframe(df, use_container_width=True)
    
    with st.expander("View Summary JSON"):
        st.json(summary)
    
    # Download
    st.sidebar.header("Download")
    
    csv_data = df.to_csv(index=False)
    st.sidebar.download_button(
        "Download CSV",
        csv_data,
        file_name=f"{selected_run.name}_results.csv",
        mime="text/csv",
    )
    
    st.sidebar.download_button(
        "Download Summary JSON",
        json.dumps(summary, indent=2),
        file_name=f"{selected_run.name}_summary.json",
        mime="application/json",
    )


if __name__ == "__main__":
    main()
