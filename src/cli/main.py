"""
CLI tool for the Cost Report AI pipeline.

Usage:
    # Run full pipeline on a file
    cost-report-ai run data/samples/hospital_gl.csv --facility hospital

    # List all CMS cost centers for a facility type
    cost-report-ai centers hospital

    # Parse a file only (no classification)
    cost-report-ai parse data/samples/hospital_gl.csv

    # Generate a sample test file
    cost-report-ai sample hospital --rows 50

    # Start the API server
    cost-report-ai serve

    # View audit trail
    cost-report-ai lineage
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

from src.config import settings
from src.core.models import FacilityType
from src.core.pipline import Pipeline
from src.facilities.registry import get_registry, list_all_cost_centers

console = Console()


@click.group()
@click.version_option(version=settings.APP_VERSION)
def cli():
    """Cost Report AI — Medicare cost report preparation pipeline."""


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--facility", "-f", type=click.Choice(["hospital", "snf", "hospice", "hha"]),
              default="hospital", help="Facility type")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output file path")
@click.option("--provider", "-p", default="Test Provider", help="Provider name")
@click.option("--fye", default="2026-12-31", help="Fiscal year end (YYYY-MM-DD)")
@click.option("--no-llm", is_flag=True, default=False, help="Skip LLM (use rule-based fallback)")
def run(file_path: str, facility: str, output: str | None, provider: str, fye: str, no_llm: bool):
    """Run the full pipeline on a file: parse → classify → export."""
    ft = FacilityType(facility)
    pipe = Pipeline(
        facility_type=ft,
        provider_name=provider,
        fiscal_year_end=fye,
    )

    # Step 1: Parse
    console.print(f"[bold]Parsing:[/bold] {file_path}")
    with console.status("Parsing file..."):
        ingestion = pipe.parse_file(file_path)
    console.print(f"  OK {ingestion.row_count} rows parsed, {ingestion.error_count} errors")

    # Step 2: Classify
    console.print(f"[bold]Classifying...[/bold]")
    with console.status("Running AI classification..."):
        classification = pipe.classify(ingestion)
    summary = classification.summary
    console.print(f"  OK {summary['total']} classified: "
                  f"[green]{summary['high_confidence']} high[/green] | "
                  f"[yellow]{summary['medium_confidence']} med[/yellow] | "
                  f"[red]{summary['low_confidence']} low[/red] | "
                  f"[bold]{summary['unallowable']} unallowable[/bold]")

    # Step 3: Export
    output_path = output or str(
        settings.OUTPUT_DIR / f"export_{ft.value}_{classification.id[:8]}.xlsx"
    )
    console.print(f"[bold]Exporting to:[/bold] {output_path}")
    with console.status("Generating HFS workbook..."):
        export = pipe.export(classification, output_path=output_path)
    console.print(f"  OK {len(export.hfs_ai_rows)} HFS AI rows exported")

    # Print session summary
    console.print(Panel(
        f"[bold]Session:[/bold] {pipe.session.id}\n"
        f"[bold]Facility:[/bold] {ft.value.upper()}\n"
        f"[bold]Provider:[/bold] {provider}\n"
        f"[bold]Output:[/bold] {output_path}\n"
        f"[bold]Lineage:[/bold] {pipe.lineage.session_id}",
        title="Pipeline Complete",
    ))


@cli.command()
@click.option("--facility", "-f", type=click.Choice(["hospital", "snf", "hospice", "hha"]),
              default=None, help="Filter by facility type")
@click.option("--search", "-s", default=None, help="Search cost centers by keyword")
def centers(facility: str | None, search: str | None):
    """List CMS cost centers for one or all facility types."""
    ft = FacilityType(facility) if facility else None

    if ft:
        reg = get_registry(ft)
        centers_data = reg.cost_centers
        table = Table(title=f"{ft.value.upper()} — {reg.form_number} Cost Centers")
        table.add_column("Code", style="cyan", width=6)
        table.add_column("Name", style="white", width=45)
        table.add_column("Category", style="yellow", width=18)
        table.add_column("Worksheet", width=10)
        table.add_column("Allowable", width=10)

        for code, cc in sorted(centers_data.items()):
            if search and search.lower() not in cc.name.lower() and search.lower() not in cc.description.lower():
                continue
            allowable = "[green]Yes[/green]" if cc.allowable else "[red]No[/red]"
            table.add_row(
                code, cc.name, cc.category.value,
                cc.worksheet, allowable,
            )

        console.print(table)
        console.print(f"\nStep-down sequence: {', '.join(reg.step_down_sequence)}")
    else:
        all_centers = list_all_cost_centers()
        for ft_name, centers in all_centers.items():
            console.print(f"\n[bold]{ft_name.upper()}[/bold] — {len(centers)} cost centers")
            for code, info in sorted(centers.items()):
                console.print(f"  [cyan]{code}[/cyan] {info['name']} ({info['category']})")


@cli.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--type", "-t", "file_type",
              type=click.Choice(["trial_balance", "census", "payroll", "psr"]),
              default=None, help="Parser type (auto-detected if omitted)")
def parse(file_path: str, file_type: str | None):
    """Parse a file without running classification."""
    pipe = Pipeline(facility_type=FacilityType.HOSPITAL)
    result = pipe.parse_file(file_path, file_type=file_type)

    console.print(f"[bold]Parsed:[/bold] {result.source_file}")
    console.print(f"  Rows: {result.row_count}")
    console.print(f"  Errors: {result.error_count}")
    console.print(f"  Type: {result.entry_type.value}")
    console.print(f"  Time: {result.processing_time_ms}ms")
    console.print(f"  Column mapping: {json.dumps(result.column_mapping, indent=2)}")

    if result.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for err in result.errors[:5]:
            console.print(f"  Row {err.get('row')}: {err.get('error')}")

    # Preview first 5 entries
    console.print("\n[bold]Preview (first 5):[/bold]")
    for entry in result.entries[:5]:
        console.print(
            f"  {entry.account_number:12s} {entry.account_description:40s} "
            f"DR: {float(entry.debit_amount):>10.2f} CR: {float(entry.credit_amount):>10.2f}"
        )


@cli.command()
@click.option("--facility", "-f", type=click.Choice(["hospital", "snf", "hospice", "hha"]),
              default="hospital", help="Facility type")
@click.option("--rows", "-r", default=20, help="Number of sample rows")
def sample(facility: str, rows: int):
    """Generate a sample GL trial balance CSV file for testing."""
    import random
    import csv

    ft = FacilityType(facility)
    reg = get_registry(ft)

    # Sample account templates
    templates = [
        ("6{0:03d}", "RN Salaries - {name}", 50000, 200000),
        ("7{0:03d}", "Medical Supplies - {name}", 5000, 80000),
        ("8{0:03d}", "Equipment Maintenance - {name}", 1000, 15000),
        ("5{0:03d}", "Office Expenses - {name}", 500, 10000),
        ("4{0:03d}", "Professional Fees - {name}", 2000, 50000),
    ]

    sample_path = settings.SAMPLES_DIR / f"sample_{ft.value}_gl.csv"

    with open(sample_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Account #", "Description", "Debit", "Credit", "Department"])

        random.seed(42)
        for i in range(rows):
            template = random.choice(templates)
            cc_list = list(reg.revenue_center_codes + reg.general_service_codes)
            center_code = random.choice(cc_list)
            cc = reg.get_cost_center(center_code)
            name = cc.name if cc else f"Center {center_code}"

            acct = template[0].format(i)
            desc = template[1].format(name=name)
            debit = round(random.uniform(*template[2:4]), 2)
            credit = round(random.uniform(0, 1000), 2)

            writer.writerow([acct, desc, debit, credit, f"DEPT{i % 10 + 1:02d}"])

    console.print(f"[green]OK - Generated {rows} sample rows:[/green] {sample_path}")


@cli.command()
@click.option("--host", default=settings.HOST, help="Host to bind to")
@click.option("--port", default=settings.PORT, type=int, help="Port to listen on")
def serve(host: str, port: int):
    """Start the FastAPI server."""
    import uvicorn
    from src.api.main import create_app

    app = create_app()
    console.print(f"[bold]Cost Report AI API[/bold]")
    console.print(f"  Listening on http://{host}:{port}")
    console.print(f"  Docs: http://{host}:{port}/docs")
    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.option("--session", default=None, help="Filter by session ID")
@click.option("--limit", default=50, type=int, help="Max entries")
def lineage(session: str | None, limit: int):
    """View the audit trail."""
    from src.core.lineage import LineageLogger

    logger = LineageLogger()
    if session:
        entries = logger.get_session_trail(session)
    else:
        entries = logger.get_all_entries(limit=limit)

    if not entries:
        console.print("[yellow]No lineage entries found.[/yellow]")
        return

    table = Table(title=f"Audit Trail ({len(entries)} entries)")
    table.add_column("Time", width=20)
    table.add_column("Action", width=12)
    table.add_column("Entity Type", width=16)
    table.add_column("Entity ID", width=16)
    table.add_column("Actor", width=10)
    table.add_column("Reason")

    for e in entries[:limit]:
        table.add_row(
            e.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            e.action,
            e.entity_type,
            e.entity_id[:12],
            e.actor,
            (e.reason or "")[:60],
        )

    console.print(table)


if __name__ == "__main__":
    cli()
