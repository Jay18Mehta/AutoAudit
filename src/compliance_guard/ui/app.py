"""Streamlit frontend for Compliance Guard."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from compliance_guard.compliance.analyzer import ComplianceAnalyzer
from compliance_guard.compliance.models import (
    FileComplianceResult,
    RepositoryComplianceReport,
    RiskSummary,
    Severity,
)
from compliance_guard.config.settings import Settings
from compliance_guard.fixing import apply_fixes_from_report
from compliance_guard.indexing.index_builder import IndexBuilder
from compliance_guard.llm.base import LLMConfig
from compliance_guard.llm.gemini_client import GeminiClient
from compliance_guard.rag.qa_service import CodebaseQAService
from compliance_guard.reporting.json_report import load_json_report, write_json_report
from compliance_guard.reporting.markdown_report import write_markdown_report
from compliance_guard.scanner.file_scanner import FileScanner
from compliance_guard.security.redactor import ContentRedactor

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Compliance Guard",
    page_icon="🛡️",
    layout="wide",
)

# ---------------------------------------------------------------------------
# Severity colours
# ---------------------------------------------------------------------------
SEVERITY_COLORS = {
    "critical": "#d32f2f",
    "high": "#f57c00",
    "medium": "#fbc02d",
    "low": "#1976d2",
    "info": "#757575",
}

SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _state_dir(repo: Path) -> Path:
    return (repo.resolve() / ".compliance_guard").resolve()


def _build_llm(settings: Settings, model_override: str | None = None) -> GeminiClient:
    cfg = LLMConfig(
        model=model_override or settings.gemini_model,
        temperature=settings.gemini_temperature,
        max_output_tokens=settings.gemini_max_output_tokens,
    )
    return GeminiClient(api_key=settings.gemini_api_key.strip(), config=cfg)


def _run_scan(
    repo: Path,
    settings: Settings,
    redact: bool,
    concurrency: int,
    model: str | None,
) -> RepositoryComplianceReport:
    llm = _build_llm(settings, model)
    scanner = FileScanner()
    entries = scanner.scan(repo)
    index = IndexBuilder().build(repo, entries)
    analyzer = ComplianceAnalyzer(
        llm=llm,
        redactor=ContentRedactor(),
        redact=redact,
        max_concurrent=concurrency,
    )
    report = asyncio.run(analyzer.analyze_repository(index))
    out_dir = _state_dir(repo)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json_report(report, out_dir / "scan_result.json")
    write_markdown_report(report, out_dir / "report.md")
    return report


def _run_ask(
    repo: Path,
    question: str,
    settings: Settings,
    redact: bool,
    model: str | None,
) -> str:
    llm = _build_llm(settings, model)
    qa = CodebaseQAService(llm=llm)
    return asyncio.run(qa.answer(repo, question, redact=redact))


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("Compliance Guard")
    st.caption("SOC 2 / HIPAA / ISO 27001 scanner")
    st.divider()

    repo_path = st.text_input(
        "Repository path",
        placeholder="/path/to/your/repo",
    )

    page = st.radio(
        "Navigation",
        ["Scan", "Report", "Ask"],
        horizontal=True,
    )

    st.divider()
    with st.expander("Settings"):
        redact = st.toggle("Redact secrets before LLM", value=True)
        concurrency = st.slider("Concurrency", 1, 10, 3)
        model_override = st.text_input("Model override", placeholder="default from .env")
        if not model_override:
            model_override = None

# ---------------------------------------------------------------------------
# Validate repo path
# ---------------------------------------------------------------------------

def _validate_repo() -> Path | None:
    if not repo_path:
        st.info("Enter a repository path in the sidebar to get started.")
        return None
    p = Path(repo_path)
    if not p.is_dir():
        st.error(f"Directory not found: `{repo_path}`")
        return None
    return p


def _validate_settings() -> Settings | None:
    try:
        settings = Settings()
        if not settings.gemini_api_key.strip():
            st.error(
                "Missing `GEMINI_API_KEY`. Set it in your `.env` file or environment."
            )
            return None
        return settings
    except Exception as exc:
        st.error(f"Configuration error: {exc}")
        return None


# ---------------------------------------------------------------------------
# Dashboard widgets
# ---------------------------------------------------------------------------

def _render_risk_metrics(summary: RiskSummary) -> None:
    cols = st.columns(5)
    cols[0].metric("Total Violations", summary.total_violations)
    cols[1].metric("Files Analyzed", summary.files_analyzed)
    cols[2].metric("Files with Issues", summary.files_with_issues)
    clean = summary.files_analyzed - summary.files_with_issues
    cols[3].metric("Clean Files", clean)
    pct = (
        round(100 * clean / summary.files_analyzed)
        if summary.files_analyzed
        else 100
    )
    cols[4].metric("Clean %", f"{pct}%")


def _render_severity_chart(summary: RiskSummary) -> None:
    if not summary.by_severity:
        return
    import pandas as pd

    rows = []
    for sev in SEVERITY_ORDER:
        count = summary.by_severity.get(sev, 0)
        if count:
            rows.append({"Severity": sev.title(), "Count": count})
    if not rows:
        return
    df = pd.DataFrame(rows)
    st.bar_chart(df, x="Severity", y="Count", color=None, horizontal=False)


def _render_standard_chart(summary: RiskSummary) -> None:
    if not summary.by_standard:
        return
    import pandas as pd

    rows = [{"Standard": k, "Count": v} for k, v in summary.by_standard.items()]
    df = pd.DataFrame(rows).sort_values("Count", ascending=False)
    st.bar_chart(df, x="Standard", y="Count")


def _render_violations_table(results: list[FileComplianceResult]) -> None:
    import pandas as pd

    rows = []
    for fr in results:
        for v in fr.violations:
            rows.append(
                {
                    "File": fr.file,
                    "Standard": v.standard,
                    "Severity": v.severity.value.title(),
                    "Issue": v.issue,
                    "Fix": v.fix,
                }
            )
    if not rows:
        st.success("No violations found.")
        return

    df = pd.DataFrame(rows)

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        sev_filter = st.multiselect(
            "Filter by severity",
            options=[s.title() for s in SEVERITY_ORDER],
            default=[s.title() for s in SEVERITY_ORDER],
        )
    with col2:
        standards = sorted(df["Standard"].unique())
        std_filter = st.multiselect(
            "Filter by standard",
            options=standards,
            default=standards,
        )

    filtered = df[df["Severity"].isin(sev_filter) & df["Standard"].isin(std_filter)]
    st.dataframe(filtered, use_container_width=True, hide_index=True)


def _render_file_details(results: list[FileComplianceResult]) -> None:
    files_with_violations = [r for r in results if r.violations]
    if not files_with_violations:
        return

    selected = st.selectbox(
        "Inspect file",
        options=[r.file for r in files_with_violations],
    )
    result = next(r for r in files_with_violations if r.file == selected)

    for i, v in enumerate(result.violations):
        color = SEVERITY_COLORS.get(v.severity.value, "#757575")
        with st.expander(
            f"**{v.severity.value.upper()}** | {v.standard} — {v.issue}",
            expanded=(v.severity.value in ("critical", "high")),
        ):
            st.markdown(f"**Explanation:** {v.explanation}")
            st.markdown(f"**Suggested fix:** {v.fix}")
            if v.fixed_code:
                st.code(v.fixed_code, language="python")

    if result.secure_patterns:
        st.markdown("**Secure patterns detected:**")
        for sp in result.secure_patterns:
            st.markdown(f"- {sp}")


def _render_report(report: RepositoryComplianceReport) -> None:
    st.subheader("Risk Overview")
    _render_risk_metrics(report.risk_summary)

    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("By Severity")
        _render_severity_chart(report.risk_summary)
    with col_b:
        st.subheader("By Standard")
        _render_standard_chart(report.risk_summary)

    st.divider()
    st.subheader("Violations")
    _render_violations_table(report.results)

    st.divider()
    st.subheader("File Details")
    _render_file_details(report.results)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

def page_scan() -> None:
    st.header("Scan Repository")
    repo = _validate_repo()
    if repo is None:
        return

    settings = _validate_settings()
    if settings is None:
        return

    if st.button("Run Scan", type="primary", use_container_width=True):
        with st.status("Scanning repository...", expanded=True) as status:
            st.write("Indexing files...")
            try:
                report = _run_scan(repo, settings, redact, concurrency, model_override)
                st.session_state["last_report"] = report
                st.session_state["last_repo"] = str(repo)
                status.update(label="Scan complete!", state="complete")
            except Exception as exc:
                status.update(label="Scan failed", state="error")
                st.error(f"Error: {exc}")
                return

    if "last_report" in st.session_state:
        _render_report(st.session_state["last_report"])


def page_report() -> None:
    st.header("View Previous Report")
    repo = _validate_repo()
    if repo is None:
        return

    json_path = _state_dir(repo) / "scan_result.json"
    if not json_path.is_file():
        st.warning(
            f"No scan results found at `{json_path}`. Run a scan first."
        )
        return

    report = load_json_report(json_path)
    st.caption(f"Generated at: {report.generated_at_utc} | Model: {report.model}")
    _render_report(report)

    # Download options
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download JSON report",
            data=json.dumps(report.model_dump(mode="json"), indent=2),
            file_name="scan_result.json",
            mime="application/json",
        )
    with col2:
        md_path = _state_dir(repo) / "report.md"
        if md_path.is_file():
            st.download_button(
                "Download Markdown report",
                data=md_path.read_text(encoding="utf-8"),
                file_name="report.md",
                mime="text/markdown",
            )


def page_ask() -> None:
    st.header("Ask about your codebase")
    repo = _validate_repo()
    if repo is None:
        return

    settings = _validate_settings()
    if settings is None:
        return

    question = st.text_area(
        "Question",
        placeholder="Where is authentication handled? Are there any hardcoded secrets?",
    )

    if st.button("Ask", type="primary") and question:
        with st.spinner("Thinking..."):
            try:
                answer = _run_ask(repo, question, settings, redact, model_override)
                st.markdown(answer)
            except Exception as exc:
                st.error(f"Error: {exc}")


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

if page == "Scan":
    page_scan()
elif page == "Report":
    page_report()
elif page == "Ask":
    page_ask()
