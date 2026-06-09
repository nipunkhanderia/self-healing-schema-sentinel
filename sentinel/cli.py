"""
CLI entry point for schema-sentinel.
Run: sentinel --help
"""
import json
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from sentinel.registry import SchemaRegistry
from sentinel.validator import SchemaValidator
from sentinel.differ import SchemaDiffer
from sentinel.healer import TestHealer
from sentinel.writer import TestWriter
from sentinel.notifier import DriftNotifier
from sentinel.models import HealResult

app = typer.Typer(
    name="sentinel",
    help="schema-sentinel — self-healing schema validation and test generation",
    add_completion=False,
)
console = Console()


@app.command()
def register(
    name: str = typer.Argument(..., help="Schema name (e.g. 'flight_booking')"),
    path: str = typer.Argument(..., help="Path to JSON Schema file or raw JSON sample"),
):
    """Register or update a schema. Accepts JSON Schema or raw JSON sample."""
    data = json.loads(Path(path).read_text())
    registry = SchemaRegistry()
    version = registry.register(name, data)
    rprint(f"[green]✓[/green] Registered [bold]{name}[/bold] as [bold]{version.version}[/bold] (source: {version.source})")


@app.command()
def validate(
    name: str = typer.Argument(..., help="Schema name"),
    payload_path: str = typer.Argument(..., help="Path to JSON payload file"),
):
    """Validate a JSON payload against the registered schema."""
    payload = json.loads(Path(payload_path).read_text())
    validator = SchemaValidator()
    result = validator.validate(name, payload)
    if result.is_valid:
        rprint(f"[green]✓ VALID[/green] — payload matches schema [bold]{name}@{result.schema_version}[/bold]")
    else:
        rprint(f"[red]✗ INVALID[/red] — {len(result.errors)} error(s) against [bold]{name}@{result.schema_version}[/bold]")
        for err in result.errors:
            rprint(f"  [red]•[/red] {err}")


@app.command()
def diff(
    name: str = typer.Argument(..., help="Schema name to diff"),
):
    """Show drift between the two most recent schema versions."""
    differ = SchemaDiffer()
    report = differ.diff(name)
    if not report.has_drift:
        rprint(f"[green]✓ No drift[/green] detected for [bold]{name}[/bold]")
        return
    rprint(f"[yellow]⚠ Drift detected[/yellow] for [bold]{name}[/bold]: {report.summary}")
    table = Table(show_header=True, header_style="bold")
    table.add_column("Field path")
    table.add_column("Change type")
    table.add_column("Was")
    table.add_column("Now")
    table.add_column("Severity")
    for d in report.drifts:
        severity_color = {"high": "red", "medium": "yellow", "low": "green"}.get(d.severity, "white")
        table.add_row(
            d.field_path,
            d.drift_type.value,
            str(d.old_value),
            str(d.new_value),
            f"[{severity_color}]{d.severity}[/{severity_color}]",
        )
    console.print(table)


@app.command()
def heal(
    name: str = typer.Argument(..., help="Schema name"),
    tests_path: str = typer.Argument(..., help="Path to existing pytest test file to update"),
):
    """Full self-heal: detect drift → generate updated tests via LLM → write output."""
    existing_code = Path(tests_path).read_text() if Path(tests_path).exists() else "# No existing tests"
    registry = SchemaRegistry()
    latest = registry.get_latest(name)
    if not latest:
        rprint(f"[red]✗[/red] No schema registered for '{name}'. Run: sentinel register {name} <path>")
        raise typer.Exit(1)

    differ = SchemaDiffer(registry)
    report = differ.diff(name)

    if not report.has_drift:
        rprint(f"[green]✓ No drift detected[/green] — tests are up to date.")
        raise typer.Exit(0)

    rprint(f"[yellow]⚠ Drift detected:[/yellow] {report.summary}")
    rprint("[cyan]→ Generating updated tests via LLM...[/cyan]")

    healer = TestHealer()
    generated_code = healer.generate_tests(report, existing_code, latest.schema_dict)

    writer = TestWriter()
    write_result = writer.write(name, generated_code, report)

    heal_result = HealResult(
        success=True,
        schema_name=name,
        drift_report=report,
        generated_test_code=generated_code,
        output_path=write_result["path"],
        pr_url=write_result.get("pr_url", ""),
    )

    notifier = DriftNotifier()
    notifier.notify(heal_result)

    rprint(f"[green]✓ Tests generated:[/green] {write_result['path']}")
    if write_result.get("pr_url"):
        rprint(f"[green]✓ PR opened:[/green] {write_result['pr_url']}")


@app.command(name="list")
def list_schemas():
    """List all registered schema names."""
    registry = SchemaRegistry()
    schemas = registry.list_schemas()
    if not schemas:
        rprint("[dim]No schemas registered yet.[/dim]")
        return
    for s in schemas:
        versions = registry.get_all_versions(s)
        rprint(f"  [bold]{s}[/bold] — {len(versions)} version(s), latest: {versions[-1].version}")


if __name__ == "__main__":
    app()
