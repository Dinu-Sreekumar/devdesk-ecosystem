import json
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
    is_service_online,
    SNIPPETVAULT_URL,
    NETWATCH_URL,
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
    ports: str = typer.Option("8000,3000,5173,8080", "--ports", "-p", help="Comma-separated dev ports to probe via NetWatch"),
    tag: str = typer.Option("general", "--tag", "-t", help="Category tag for this session"),
    notes: str = typer.Option("", "--notes", "-n", help="Contextual notes for this session")
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
    metadata = {
        "active_dev_ports": active_ports,
        "tag": tag,
        "notes": notes
    }
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
def status(
    id_only: bool = typer.Option(False, "--id-only", help="Print only active session ID (or latest if none active)"),
    json_output: bool = typer.Option(False, "--json", help="Output session data in JSON format")
):
    """
    Show current active session details.
    """
    current = get_active_session()
    
    if id_only:
        if current:
            console.print(current["id"])
        else:
            latest = list_sessions(limit=1)
            if latest:
                console.print(latest[0]["id"])
            else:
                console.print("")
        return

    if json_output:
        console.print(json.dumps(current or {}))
        return

    if not current:
        console.print("[dim]No active focus session.[/dim]")
        return

    console.print(f"[bold cyan]Active Session:[/bold cyan] {current['title']}")
    console.print(f"  • ID: [cyan]{current['id']}[/cyan]")
    console.print(f"  • Started At: {current['started_at']}")
    console.print(f"  • Planned Duration: {current['duration_minutes']} min")
    meta = current.get("metadata", {})
    if meta.get("tag"):
        console.print(f"  • Tag: [magenta]{meta['tag']}[/magenta]")
    ports = meta.get("active_dev_ports", [])
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


def _render_session_table(limit: int = 10, tag: Optional[str] = None, json_output: bool = False):
    sessions = list_sessions(limit=limit)
    if tag:
        sessions = [s for s in sessions if tag.lower() in s.get("metadata", {}).get("tag", "").lower()]

    if json_output:
        console.print(json.dumps(sessions))
        return

    if not sessions:
        console.print("[yellow]No logged sessions found.[/yellow]")
        return

    table = Table(title="WorkPulse Session History", show_header=True, header_style="bold cyan")
    table.add_column("Session ID", style="dim", width=16)
    table.add_column("Title", style="bold")
    table.add_column("Tag", style="magenta", width=10)
    table.add_column("Duration", justify="right", width=9)
    table.add_column("Status", width=11)
    table.add_column("Dev Ports", style="green", width=12)
    table.add_column("Snippets", justify="right", width=9)
    table.add_column("Date", style="dim", width=19)

    for s in sessions:
        status_style = "green" if s["status"] == "COMPLETED" else "red" if s["status"] == "ABORTED" else "yellow"
        meta = s.get("metadata", {})
        s_tag = meta.get("tag", "general")
        ports = ", ".join(map(str, meta.get("active_dev_ports", []))) or "-"
        snippet_count = str(meta.get("snippet_count", 0))

        table.add_row(
            s["id"],
            s["title"],
            s_tag,
            f"{s['duration_minutes']}m",
            f"[{status_style}]{s['status']}[/{status_style}]",
            ports,
            snippet_count,
            s["started_at"][:19].replace("T", " ")
        )

    console.print(table)


@app.command(name="log")
def log_cmd(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of past sessions to display"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter history by tag substring"),
    json_output: bool = typer.Option(False, "--json", help="Output history in JSON format")
):
    """
    View table of past focus sessions.
    """
    _render_session_table(limit=limit, tag=tag, json_output=json_output)


@app.command(name="history")
def history_cmd(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of past sessions to display"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter history by tag substring"),
    json_output: bool = typer.Option(False, "--json", help="Output history in JSON format")
):
    """
    Alias for 'workpulse log': View table of past focus sessions.
    """
    _render_session_table(limit=limit, tag=tag, json_output=json_output)


@app.command()
def stats(
    json_output: bool = typer.Option(False, "--json", help="Output statistics in JSON format")
):
    """
    Calculate aggregate productivity metrics across all stored sessions.
    """
    sessions = list_sessions(limit=1000)
    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s["status"] == "COMPLETED")
    aborted_sessions = sum(1 for s in sessions if s["status"] == "ABORTED")
    total_minutes = sum(s["duration_minutes"] for s in sessions if s["status"] == "COMPLETED")
    total_snippets = sum(s.get("metadata", {}).get("snippet_count", 0) for s in sessions)

    completion_rate = round((completed_sessions / total_sessions * 100), 1) if total_sessions > 0 else 0.0

    if json_output:
        console.print(json.dumps({
            "total_sessions": total_sessions,
            "completed": completed_sessions,
            "aborted": aborted_sessions,
            "total_focus_minutes": total_minutes,
            "completion_rate_pct": completion_rate,
            "snippets_linked": total_snippets,
        }))
        return

    table = Table(title="WorkPulse Focus Analytics", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="green", justify="right")

    table.add_row("Total Focus Sessions", str(total_sessions))
    table.add_row("Completed Sessions", str(completed_sessions))
    table.add_row("Aborted / Interrupted", str(aborted_sessions))
    table.add_row("Completion Rate", f"{completion_rate}%")
    table.add_row("Total Focus Time", f"{total_minutes} mins ({round(total_minutes/60, 1)} hrs)")
    table.add_row("Snippets Linked", str(total_snippets))

    console.print(table)


@app.command()
def peers(
    json_output: bool = typer.Option(False, "--json", help="Output peer statuses in JSON format")
):
    """
    Probe the health of peer DevDesk services (SnippetVault and NetWatch).
    """
    vault_online = is_service_online(SNIPPETVAULT_URL)
    netwatch_online = is_service_online(NETWATCH_URL)

    if json_output:
        console.print(json.dumps([
            {"service": "snippetvault", "port": 8765, "online": vault_online},
            {"service": "netwatch", "port": 8766, "online": netwatch_online}
        ]))
        return

    table = Table(title="DevDesk Local Peer Services", show_header=True, header_style="bold cyan")
    table.add_column("Service", style="bold")
    table.add_column("Port", justify="center", width=8)
    table.add_column("Endpoint", style="dim")
    table.add_column("Status", justify="center", width=14)

    v_status = "[green]● ONLINE[/green]" if vault_online else "[red]○ OFFLINE[/red]"
    n_status = "[green]● ONLINE[/green]" if netwatch_online else "[red]○ OFFLINE[/red]"

    table.add_row("SnippetVault", "8765", SNIPPETVAULT_URL, v_status)
    table.add_row("NetWatch", "8766", NETWATCH_URL, n_status)

    console.print(table)