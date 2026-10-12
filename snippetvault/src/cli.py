import sys
from  typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

from snippetvault.src.database import(
    init_db,
    create_snippet,
    get_snippet,
    list_snippets,
    delete_snippet
)

app = typer.Typer(help= "SnippetVault: Offline developer snippet and command stash")
console = Console()

@app.callback()
def main_callback():
    """

    Runs before any Command: guarantees the database table and indexes exists.
    """
    init_db()
@app.command()
def save(
    title: str = typer.Argument(..., help="Short summary or title of the snippet"),
    code: Optional[str] = typer.Argument(None, help="The code snippet text (optional if piped via stdin)"),
    lang: str = typer.Option("text","--lang", "-l", help="The Language for syntax highlighting"),
    tag: str = typer.Option("","--tag","-t", help="Comma-seperated tags (e.g. 'Python,api')"),
    session: Optional[str] = typer.Option(None, "--session","-s", help="WorkPulse session ID")
):
    """

    Save a snippet. Reads either from the argument or piped standard input (stdin).
    """

    #1. Detect if code is being piped through standard input: cat file.py | vault save "Title"
    if not sys.stdin.isatty():
        piped_content = sys.stdin.read().strip()
        if piped_content:
            code = piped_content
    
    #2. If cofr is still missing, require the user to provide it.
    if not code:
        console.print("[red]Error:[/red] Snippet code must be provided as an arguement or via stdin.")
        raise typer.Exit(code=1)
    
    #3. Persist to SqLite
    snippet_id= create_snippet(
        title=title,
        code=code,
        language=lang,
        tags=tag,
        session_id=session
    )

    console.print(f"[green]✓ Saved snippet #{snippet_id} : [/green] [bold] {title} [/bold] ({lang})")


@app.command(name="list")
def list_cmd(
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum number of snippets to display"),
    tag: Optional[str] = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    lang: Optional[str] = typer.Option(None, "--lang", "-l", help="Filter by language"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Filter by session ID"),
    query: Optional[str] = typer.Option(None, "--query", "--search", "-q", help="Search substring across title, code, and tags")
):
    """
    List saved snippets in a formatted table.
    """
    snippets = list_snippets(tag=tag, language=lang, session_id=session, query=query, limit=limit)

    if not snippets:
        console.print("[yellow]No snippets found matching criteria.[/yellow]")
        return

    table = Table(title="SnippetVault", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Title", style="bold")
    table.add_column("Lang", style="green", width=12)
    table.add_column("Tags", style="magenta")
    table.add_column("Created", style="dim", width=20)

    for s in snippets:
        table.add_row(
            str(s["id"]),
            s["title"],
            s["language"],
            s["tags"] or "-",
            str(s["created_at"])
        )

    console.print(table)


@app.command()
def get(
    snippet_id: int = typer.Argument(..., help="ID of the snippet to retrieve")
):
    """
    View a snippet with syntax highlighting.
    """
    snippet = get_snippet(snippet_id)
    if not snippet:
        console.print(f"[red]Error:[/red] Snippet #{snippet_id} not found.")
        raise typer.Exit(code=1)

    # Render code with Rich syntax highlighting
    syntax = Syntax(snippet["code"], snippet["language"], theme="monokai", line_numbers=True)
    panel = Panel(
        syntax,
        title=f"#{snippet['id']} - {snippet['title']}",
        subtitle=f"Lang: {snippet['language']} | Tags: {snippet['tags'] or 'none'}",
        expand=False
    )
    console.print(panel)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search term across title, code, and tags")
):
    """
    Search snippets by text substring.
    """
    results = list_snippets(query=query)

    if not results:
        console.print(f"[yellow]No snippets found matching '{query}'.[/yellow]")
        return

    table = Table(title=f"Search Results for '{query}'", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Title", style="bold")
    table.add_column("Lang", style="green", width=12)
    table.add_column("Tags", style="magenta")

    for s in results:
        table.add_row(str(s["id"]), s["title"], s["language"], s["tags"] or "-")

    console.print(table)


@app.command()
def delete(
    snippet_id: int = typer.Argument(..., help="ID of snippet to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt")
):
    """
    Delete a snippet by ID.
    """
    if not yes:
        confirm = typer.confirm(f"Are you sure you want to delete snippet #{snippet_id}?")
        if not confirm:
            console.print("[yellow]Deletion cancelled.[/yellow]")
            return

    success = delete_snippet(snippet_id)
    if success:
        console.print(f"[green]✓ Deleted snippet #{snippet_id}.[/green]")
    else:
        console.print(f"[red]Error:[/red] Snippet #{snippet_id} not found.")
        raise typer.Exit(code=1)

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host address"),
    port: int = typer.Option(8765, "--port", "-p", help="Bind port number"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload for development")
):
    """
    Launch the background SnippetVault REST API daemon.
    """
    import uvicorn
    from snippetvault.src.server import app as server_app
    console.print(f"[green]Starting SnippetVault daemon on http://{host}:{port}...[/green]")
    if reload:
        uvicorn.run("snippetvault.src.server:app", host=host, port=port, reload=True)
    else:
        uvicorn.run(server_app, host=host, port=port)