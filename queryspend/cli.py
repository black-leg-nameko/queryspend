"""Typer command-line interface; all calculation lives in shared libraries."""

from __future__ import annotations

import json
import os
import tempfile
from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer

from queryspend.demo import build_demo_report
from queryspend.engine import evaluate
from queryspend.exceptions import QuerySpendError
from queryspend.models import EvaluationRequest, QuerySpendReport
from queryspend.renderers import JsonRenderer, MarkdownRenderer, TerminalRenderer
from queryspend.validation import evaluate_validation

app = typer.Typer(
    name="queryspend",
    help="Estimate recurring BigQuery cost changes in dbt pull requests.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)


class OutputFormat(StrEnum):
    TERMINAL = "terminal"
    MARKDOWN = "markdown"
    JSON = "json"


@app.command()
def demo(
    format_: Annotated[
        OutputFormat,
        typer.Option("--format", help="Output format (terminal or json)."),
    ] = OutputFormat.TERMINAL,
    output: Annotated[Path | None, typer.Option(help="Optional report output path.")] = None,
) -> None:
    """Run the credential-free synthetic northstar_retail scenario."""

    if format_ is OutputFormat.MARKDOWN:
        _fail("demo supports --format terminal or json", 2)
    try:
        report = build_demo_report()
        rendered = _render(report, format_)
        if output is not None:
            _atomic_write(output, JsonRenderer().render(report))
        typer.echo(rendered, nl=False)
        if report.policy.decision.value == "block":
            raise typer.Exit(3)
    except QuerySpendError as error:
        _handle_error(error, output=output, format_=format_)
    except typer.Exit:
        raise
    except Exception:
        _fail("unexpected internal error; rerun with local debugging enabled", 6)


@app.command()
def check(
    base: Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)],
    head: Annotated[Path, typer.Option(exists=True, dir_okay=False, readable=True)],
    config: Annotated[Path | None, typer.Option(exists=True, dir_okay=False)] = None,
    output: Annotated[Path, typer.Option(help="Atomic JSON report path.")] = Path(
        "queryspend-report.json"
    ),
    format_: Annotated[
        OutputFormat,
        typer.Option("--format", help="Output format (terminal or json)."),
    ] = OutputFormat.TERMINAL,
    no_progress: Annotated[bool, typer.Option(help="Disable TTY progress output.")] = False,
) -> None:
    """Evaluate base and head dbt manifests with BigQuery dry-run evidence."""

    _ = no_progress  # Progress output is intentionally absent from non-interactive v1.
    if format_ is OutputFormat.MARKDOWN:
        _fail("check supports --format terminal or json; use render for Markdown", 2)
    try:
        report = evaluate(
            EvaluationRequest(base_manifest=base, head_manifest=head, config=config)
        )
        _atomic_write(output, JsonRenderer().render(report))
        typer.echo(_render(report, format_), nl=False)
        if report.policy.decision.value == "block":
            raise typer.Exit(3)
    except QuerySpendError as error:
        _handle_error(error, output=output, format_=format_)
    except typer.Exit:
        raise
    except Exception:
        _fail("unexpected internal error; no provider text or SQL was logged", 6)


@app.command()
def render(
    input_: Annotated[Path, typer.Option("--input", exists=True, dir_okay=False)],
    format_: Annotated[
        OutputFormat,
        typer.Option("--format", help="Output format (terminal, markdown, or json)."),
    ],
) -> None:
    """Render a saved Cost Change Manifest without provider access."""

    try:
        report = QuerySpendReport.model_validate_json(input_.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        _fail(f"Invalid report {input_}: report does not match the queryspend schema", 2)
    try:
        typer.echo(_render(report, format_), nl=False)
    except Exception:
        _fail("unexpected internal rendering error", 6)


@app.command(name="validate")
def validate_command(
    predictions: Annotated[str, typer.Option(help="Quoted glob of prediction reports.")],
    observations: Annotated[Path, typer.Option(exists=True, dir_okay=False)],
    output: Annotated[Path, typer.Option(help="Atomic validation report path.")] = Path(
        "validation-report.json"
    ),
) -> None:
    """Evaluate the immutable technical-gate-v1 accuracy profile."""

    try:
        report = evaluate_validation(predictions, observations)
        rendered = json.dumps(
            report.model_dump(mode="json", by_alias=True), indent=2, sort_keys=True
        ) + "\n"
        _atomic_write(output, rendered)
        typer.echo(rendered, nl=False)
    except QuerySpendError as error:
        _handle_error(error, output=None, format_=OutputFormat.JSON)
    except Exception:
        _fail("unexpected internal validation error", 6)


def _render(report: QuerySpendReport, format_: OutputFormat) -> str:
    if format_ is OutputFormat.JSON:
        return JsonRenderer().render(report)
    if format_ is OutputFormat.MARKDOWN:
        return MarkdownRenderer().render(report)
    return TerminalRenderer().render(report)


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory_descriptor = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_descriptor)
        finally:
            os.close(directory_descriptor)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _handle_error(
    error: QuerySpendError,
    *,
    output: Path | None,
    format_: OutputFormat,
) -> None:
    if error.partial_report is not None:
        if output is not None:
            _atomic_write(output, JsonRenderer().render(error.partial_report))
        typer.echo(_render(error.partial_report, format_), nl=False)
    typer.echo(f"queryspend: {error}", err=True)
    raise typer.Exit(error.exit_code)


def _fail(message: str, code: int) -> None:
    typer.echo(f"queryspend: {message}", err=True)
    raise typer.Exit(code)


if __name__ == "__main__":
    app()
