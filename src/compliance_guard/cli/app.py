"""Typer CLI: ``compliance scan|report|ask``."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import typer
from dotenv import load_dotenv
from rich.logging import RichHandler

from compliance_guard.compliance.analyzer import ComplianceAnalyzer
from compliance_guard.config.settings import Settings
from compliance_guard.indexing.index_builder import IndexBuilder
from compliance_guard.llm.base import LLMConfig
from compliance_guard.llm.gemini_client import GeminiClient
from compliance_guard.reporting.cli_table import print_cli_summary
from compliance_guard.reporting.json_report import load_json_report, write_json_report
from compliance_guard.reporting.markdown_report import write_markdown_report
from compliance_guard.scanner.file_scanner import FileScanner
from compliance_guard.security.redactor import ContentRedactor
from compliance_guard.rag.qa_service import CodebaseQAService

load_dotenv()

app = typer.Typer(
    name="compliance",
    help="Repository compliance scanning (SOC2 / HIPAA / ISO 27001) with Gemini.",
    no_args_is_help=True,
)
logger = logging.getLogger("compliance_guard")


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


def _state_dir(repo: Path) -> Path:
    return (repo.resolve() / ".compliance_guard").resolve()


@app.command("scan")
def scan_cmd(
    repo: Path = typer.Argument(..., exists=True, file_okay=False, readable=True),
    redact: bool = typer.Option(
        True,
        "--redact/--no-redact",
        help="Mask emails/tokens/password-like assignments before LLM calls.",
    ),
    model: str | None = typer.Option(None, "--model", "-m"),
    concurrency: int = typer.Option(3, "--concurrency", "-c", help="Parallel file analyses."),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Scan a repository and run Gemini compliance analysis."""
    _configure_logging(verbose)
    settings = Settings()
    api_key = settings.gemini_api_key.strip()
    if not api_key:
        typer.echo(
            "Missing GEMINI_API_KEY. Copy .env.example to .env and set your key.",
            err=True,
        )
        raise typer.Exit(code=1)

    cfg = LLMConfig(
        model=model or settings.gemini_model,
        temperature=settings.gemini_temperature,
        max_output_tokens=settings.gemini_max_output_tokens,
    )
    llm = GeminiClient(api_key=api_key, config=cfg)
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
    json_path = out_dir / "scan_result.json"
    md_path = out_dir / "report.md"
    write_json_report(report, json_path)
    write_markdown_report(report, md_path)

    typer.echo(f"Wrote JSON: {json_path}")
    typer.echo(f"Wrote Markdown: {md_path}")
    print_cli_summary(report)


@app.command("report")
def report_cmd(
    repo: Path = typer.Argument(..., exists=True, file_okay=False, readable=True),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """Print a summary table from the last scan in ``.compliance_guard/``."""
    _configure_logging(verbose)
    path = _state_dir(repo) / "scan_result.json"
    if not path.is_file():
        typer.echo(
            f"No scan found at {path}. Run: compliance scan {repo}",
            err=True,
        )
        raise typer.Exit(code=1)
    report = load_json_report(path)
    print_cli_summary(report)


@app.command("ask")
def ask_cmd(
    repo: Path = typer.Argument(..., exists=True, file_okay=False, readable=True),
    question: str = typer.Argument(..., help="Natural-language question about the codebase."),
    redact: bool = typer.Option(True, "--redact/--no-redact"),
    model: str | None = typer.Option(None, "--model", "-m"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
) -> None:
    """RAG-style Q&A (keyword retrieval; swap in embeddings + vector DB later)."""
    _configure_logging(verbose)
    settings = Settings()
    api_key = settings.gemini_api_key.strip()
    if not api_key:
        typer.echo("Missing GEMINI_API_KEY.", err=True)
        raise typer.Exit(code=1)

    cfg = LLMConfig(
        model=model or settings.gemini_model,
        temperature=settings.gemini_temperature,
        max_output_tokens=settings.gemini_max_output_tokens,
    )
    llm = GeminiClient(api_key=api_key, config=cfg)
    qa = CodebaseQAService(llm=llm)
    answer = asyncio.run(qa.answer(repo, question, redact=redact))
    typer.echo(answer)


if __name__ == "__main__":
    app()
