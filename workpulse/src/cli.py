from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table

from workpulse.src.storage import (
    init_db,
    start_session,
    get_active_session,
    finish_session,
    list_sessions,
)
from workpulse.src.client import (
    detect_active_dev_ports,
    get_session_snippets,
)
from workpulse.src.timer import run_countdown

app = typer.Typer(help="WorkPulse: Focus session tracker with DevDesk peer integration")
console = Console()


@app.callback()
def main_callback():
    """Guarantees SQLite sessions table exists before running any command."""
    init_db()


@app.command()
def start(
    title: str = typer.Argument(..., help="Title or goal for this focus block"),
    duration: int = typer.Option(25, "--duration", "-d", help="Duration in minutes"),
    ports: str = typer.Option("8000,3000,5173,8080", "--ports", "-p", help="Comma-separated dev ports to probe via NetWatch")
):
    """
    Start a new focus session. Automatically enriches session with NetWatch and SnippetVault data.
    """
    # 1. Prevent overlapping sessions
    current = get_active_session()
    if current:
        console.print(f"[yellow]Warning:[/yellow] A session is already active: [bold]{current['title']}[/bold] (ID: {current['id']})")
        console.print("Run [bold cyan]workpulse stop[/bold cyan] before starting a new one.")
        raise typer.Exit(code=1)

    # 2. Probe NetWatch for active dev ports (300ms budget, fail-silent)
    port_list = [int(p.strip()) for p in ports.split(",") if p.strip().isdigit()]
    active_ports = detect_active_dev_ports(port_list)

    # 3. Create active session in SQLite
    metadata = {"active_dev_ports": active_ports}
    session_id = start_session(title=title, duration_minutes=duration, metadata=metadata)
    console.print(f"[green]✓ Started focus session:[/green] [bold]{title}[/bold] (ID: [cyan]{session_id}[/cyan])")

    # 4. Launch terminal countdown timer
    completed = run_countdown(
        title=title,
        session_id=session_id,
        duration_minutes=duration,
        active_ports=active_ports
    )

    # 5. On completion or interrupt: Query SnippetVault for session snippets
    snippets = get_session_snippets(session_id)
    if snippets:
        console.print(f"\n[green]Linked {len(snippets)} snippet(s) from SnippetVault to this session:[/green]")
        for s in snippets:
            console.print(f"  • #{s['id']} [bold]{s['title']}[/bold] ({s['language']})")

    # 6. Finalize session in SQLite
    status_str = "COMPLETED" if completed else "ABORTED"
    finish_session(
        session_id=session_id,
        status=status_str,
        additional_metadata={"snippet_count": len(snippets)}
    )
    console.print(f"[dim]Session marked as {status_str}.[/dim]")


@app.command()
def status():
    """
    Show current active session details.
    """
    current = get_active_session()
    if not current:
        console.print("[dim]No active focus session.[/dim]")
        return

    console.print(f"[bold cyan]Active Session:[/bold cyan] {current['title']}")
    console.print(f"  • ID: [cyan]{current['id']}[/cyan]")
    console.print(f"  • Started At: {current['started_at']}")
    console.print(f"  • Planned Duration: {current['duration_minutes']} min")
    ports = current.get("metadata", {}).get("active_dev_ports", [])
    if ports:
        console.print(f"  • Dev Ports: [green]{', '.join(map(str, ports))}[/green]")


@app.command()
def stop(
    abort: bool = typer.Option(False, "--abort", "-a", help="Mark session as ABORTED instead of COMPLETED")
):
    """
    Manually end the active session and link SnippetVault snippets.
    """
    current = get_active_session()
    if not current:
        console.print("[yellow]No active session to stop.[/yellow]")
        return

    session_id = current["id"]
    snippets = get_session_snippets(session_id)

    status_str = "ABORTED" if abort else "COMPLETED"
    finish_session(
        session_id=session_id,
        status=status_str,
        additional_metadata={"snippet_count": len(snippets)}
    )

    console.print(f"[green]✓ Stopped session #{session_id} as [bold]{status_str}[/bold].[/green]")
    if snippets:
        console.print(f"Linked {len(snippets)} snippet(s) created during this block.")


@app.command()
def log(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of past sessions to display")
):
    """
    View table of past focus sessions.
    """
    sessions = list_sessions(limit=limit)

    if not sessions:
        console.print("[yellow]No logged sessions found.[/yellow]")
        return

    table = Table(title="WorkPulse Session Log", show_header=True, header_style="bold cyan")
    table.add_column("Session ID", style="dim", width=16)
    table.add_column("Title", style="bold")
    table.add_column("Duration", justify="right", width=10)
    table.add_column("Status", width=11)
    table.add_column("Dev Ports", style="green", width=12)
    table.add_column("Snippets", justify="right", width=10)
    table.add_column("Date", style="dim", width=19)

    for s in sessions:
        status_style = "green" if s["status"] == "COMPLETED" else "red" if s["status"] == "ABORTED" else "yellow"
        meta = s.get("metadata", {})
        ports = ", ".join(map(str, meta.get("active_dev_ports", []))) or "-"
        snippet_count = str(meta.get("snippet_count", 0))

        table.add_row(
            s["id"],
            s["title"],
            f"{s['duration_minutes']}m",
            f"[{status_style}]{s['status']}[/{status_style}]",
            ports,
            snippet_count,
            s["started_at"][:19].replace("T", " ")
        )

    console.print(table)