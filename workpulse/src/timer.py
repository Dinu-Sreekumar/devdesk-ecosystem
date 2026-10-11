import time
from typing import Optional, List
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.text import Text

console = Console()


def render_display(
    title: str,
    session_id: str,
    seconds_remaining: int,
    active_ports: Optional[List[int]] = None
) -> Panel:
    """
    Constructs a Rich Panel displaying session details and formatted MM:SS countdown.
    """
    mins = seconds_remaining // 60
    secs = seconds_remaining % 60
    time_str = f"{mins:02d}:{secs:02d}"

    content = Text()
    content.append(f"Focus: {title}\n", style="bold white")
    content.append(f"Session: {session_id}\n", style="dim cyan")

    # Style the ports directly using the style parameter
    if active_ports:
        ports_str = f"Dev Server Running on port(s): {', '.join(map(str, active_ports))}\n\n"
        content.append(ports_str, style="bold green")
    else:
        content.append("No active dev servers detected\n\n", style="dim")

    # Countdown clock
    time_style = "bold green" if seconds_remaining > 60 else "bold red"
    content.append(f"  {time_str}  \n\n", style=time_style)
    content.append("Press Ctrl+C to stop session", style="dim italic")

    return Panel(
        Align.center(content),
        title="[bold cyan]WorkPulse Focus Session[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    )

def run_countdown(
    title: str,
    session_id: str,
    duration_minutes: int,
    active_ports: Optional[List[int]] = None
) -> bool:
    """
    Runs the live countdown loop.
    Returns True if completed naturally, or False if interrupted by user (Ctrl+C).
    """
    total_seconds = duration_minutes * 60

    try:
        with Live(console=console, screen=False, refresh_per_second=4) as live:
            for remaining in range(total_seconds, -1, -1):
                panel = render_display(
                    title=title,
                    session_id=session_id,
                    seconds_remaining=remaining,
                    active_ports=active_ports
                )
                live.update(panel)
                if remaining > 0:
                    time.sleep(1)

        console.print("[bold green]✓ Session completed! Time is up.[/bold green]")
        return True

    except KeyboardInterrupt:
        # User pressed Ctrl+C
        console.print("\n[yellow]Session stopped by user.[/yellow]")
        return False