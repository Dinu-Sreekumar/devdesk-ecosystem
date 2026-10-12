import json
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table

from netwatch.src.inspector import (
    is_port_in_use,
    get_port_process_info,
    scan_ports,
    check_wan_latency,
)

app = typer.Typer(help="NetWatch: Socket inspector and background health agent")
console = Console()


@app.command()
def check(
    port: int = typer.Argument(..., help="TCP port number to inspect"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress terminal output (exit code 0 if free, 1 if in use)"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-parsable JSON envelope")
):
    """
    Inspect a single port.
    Returns exit code 0 if port is free, or exit code 1 if port is in use.
    """
    info = get_port_process_info(port)

    if json_output:
        console.print(json.dumps(info))
        raise typer.Exit(code=1 if info["in_use"] else 0)

    if not info["in_use"]:
        if not quiet:
            console.print(f"[green]✓ Port {port} is FREE.[/green]")
        raise typer.Exit(code=0)

    # Port is in use
    if not quiet:
        proc = info["process"]
        if proc:
            name = proc.get("name", "unknown")
            pid = proc.get("pid", "unknown")
            user = proc.get("user", "unknown")
            console.print(
                f"[bold red]✗ Port {port} is IN USE[/bold red] by [yellow]{name}[/yellow] "
                f"(PID: {pid}, User: {user})"
            )
        else:
            console.print(f"[bold red]✗ Port {port} is IN USE[/bold red] (process details hidden)")

    raise typer.Exit(code=1)


@app.command()
def scan(
    start: int = typer.Option(3000, "--start", "-s", help="Start port of scan range"),
    end: int = typer.Option(9000, "--end", "-e", help="End port of scan range"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-parsable JSON list")
):
    """
    Scan and display all active listening TCP ports in the given range.
    """
    if not json_output:
        console.print(f"[cyan]Scanning TCP listeners between ports {start} and {end}...[/cyan]")
    listeners = scan_ports(start_port=start, end_port=end)

    if json_output:
        console.print(json.dumps(listeners))
        return

    if not listeners:
        console.print(f"[green]No active TCP listeners found in range {start}-{end}.[/green]")
        return

    table = Table(title="Active TCP Listeners", show_header=True, header_style="bold cyan")
    table.add_column("Port", style="bold yellow", width=8)
    table.add_column("Bind IP", style="dim", width=16)
    table.add_column("Process Name", style="green")
    table.add_column("PID", style="magenta", width=8)
    table.add_column("User", style="dim")

    for item in listeners:
        proc = item.get("process")
        name = proc.get("name", "-") if proc else "-"
        pid = str(proc.get("pid", "-")) if proc else "-"
        user = proc.get("user", "-") if proc else "-"

        table.add_row(
            str(item["port"]),
            item.get("ip", "0.0.0.0"),
            name,
            pid,
            user
        )

    console.print(table)


@app.command()
def ping(
    host: str = typer.Option("1.1.1.1", "--host", "-h", help="Target IP or hostname to ping"),
    port: int = typer.Option(53, "--port", "-p", help="Target TCP port (default: DNS 53)"),
    timeout: float = typer.Option(1.0, "--timeout", "-t", help="Handshake timeout in seconds"),
    json_output: bool = typer.Option(False, "--json", help="Output machine-parsable JSON envelope")
):
    """
    Verify external internet connectivity and measure handshake latency.
    """
    result = check_wan_latency(host=host, port=port, timeout=timeout)

    if json_output:
        console.print(json.dumps(result))
        raise typer.Exit(code=0 if result["reachable"] else 1)

    if result["reachable"]:
        ms = result["latency_ms"]
        console.print(f"[green]✓ {host}:{port} is REACHABLE[/green] (Latency: [bold]{ms} ms[/bold])")
        raise typer.Exit(code=0)
    else:
        err = result.get("error", "timeout")
        console.print(f"[red]✗ {host}:{port} UNREACHABLE[/red] (Error: {err})")
        raise typer.Exit(code=1)

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address"),
    port: int = typer.Option(8766, "--port", "-p", help="Bind port number"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload for development")
):
    """
    Launch the background NetWatch REST API daemon.
    """
    import uvicorn
    from netwatch.src.server import app as server_app
    console.print(f"[green]Starting NetWatch daemon on http://{host}:{port}...[/green]")
    if reload:
        uvicorn.run("netwatch.src.server:app", host=host, port=port, reload=True)
    else:
        uvicorn.run(server_app, host=host, port=port)