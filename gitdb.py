import click
import os
import json
import time
import sqlite3
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from snapshot_engine import (
    Commit, gitdb_init, save_commit, load_commit, 
    extract_schema, dump_data, generate_hash
)
from diff_engine import gitdb_diff, gitdb_checkout

load_dotenv()
DB_PATH = os.getenv("GITDB_DATABASE_PATH")
console = Console()

def get_db_path(ctx_path):
    path = ctx_path or DB_PATH
    if not path:
        console.print("[red]Error: Database connection path not found. Provide it as an argument or set GITDB_DATABASE_PATH in .env[/red]")
        raise click.Abort()
    return path

@click.group()
def cli():
    """GitDB - A versioning engine for SQLite."""
    pass

@cli.command()
@click.argument('db_path', required=False)
def init(db_path):
    """Initialize a .gitdb metadata directory."""
    try:
        path = get_db_path(db_path)
        gitdb_init(path)
        console.print(f"[bold green]Initialized GitDB metadata directory for {path}[/bold green]")
    except Exception as e:
        console.print(f"[red]Initialization failed: {e}[/red]")

@cli.command()
@click.option('-m', '--message', required=True, help='Commit message')
@click.option('--author', default=os.getlogin() if hasattr(os, 'getlogin') else 'Anonymous', help='Author name')
def commit(message, author):
    """Snapshot the current database state."""
    try:
        path = get_db_path(None)
        if not os.path.exists(path):
            console.print(f"[red]Error: Database file '{path}' not found.[/red]")
            return

        # 1. Check for primary keys (User requirement)
        conn = sqlite3.connect(path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table})")
            if not any(row[5] > 0 for row in cursor.fetchall()):
                console.print(f"[yellow]Warning: Table '{table}' has no primary key. Falling back to rowid.[/yellow]")
        conn.close()

        # 2. Extract snapshots
        schema = extract_schema(path)
        data = dump_data(path)
        
        # 3. Get parent hash
        head = load_commit(path)
        parent_hash = head.hash if head else ""
        
        # 4. Generate hash and create commit
        commit_hash = generate_hash(schema, data, parent_hash)
        
        # Check if anything changed
        if head and commit_hash == head.hash:
            console.print("[yellow]Nothing to commit, database state unchanged.[/yellow]")
            return

        new_commit = Commit(
            hash=commit_hash,
            parent_hash=parent_hash,
            message=message,
            author=author,
            timestamp=time.time(),
            schema_snapshot=schema,
            data_snapshot=json.dumps(data)
        )
        
        save_commit(new_commit, path)
        console.print(f"[bold green]Commit {commit_hash[:8]} created successfully.[/bold green]")
    except Exception as e:
        console.print(f"[red]Commit failed: {e}[/red]")

@cli.command()
@click.option('--oneline', is_flag=True, help='Show condensed single-line format')
def log(oneline):
    """Show the commit history."""
    try:
        path = get_db_path(None)
        commit = load_commit(path)
        
        if not commit:
            console.print("[yellow]No commits found.[/yellow]")
            return

        commits = []
        curr = commit
        while curr:
            commits.append(curr)
            if not curr.parent_hash:
                break
            # Load parent
            gitdb_dir = os.path.join(os.path.dirname(os.path.abspath(path)), ".gitdb")
            parent_path = os.path.join(gitdb_dir, "commits", f"{curr.parent_hash}.json")
            if os.path.exists(parent_path):
                with open(parent_path, "r") as f:
                    curr = Commit.from_json(f.read())
            else:
                break

        if oneline:
            for c in commits:
                console.print(f"[yellow]{c.hash[:8]}[/yellow] [white]{c.message}[/white] ([blue]{c.author}[/blue])")
        else:
            table = Table(title="Commit Log")
            table.add_column("Hash", style="yellow")
            table.add_column("Author", style="blue")
            table.add_column("Timestamp", style="magenta")
            table.add_column("Message", style="white")
            
            for c in commits:
                dt = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(c.timestamp))
                table.add_row(c.hash[:8], c.author, dt, c.message)
            
            console.print(table)
    except Exception as e:
        console.print(f"[red]Log failed: {e}[/red]")

def resolve_hash(short_hash, repo_path):
    """Resolves a short hash to a full hash from the commit store."""
    gitdb_dir = os.path.join(os.path.dirname(os.path.abspath(repo_path)), ".gitdb")
    commits_dir = os.path.join(gitdb_dir, "commits")
    if not os.path.exists(commits_dir):
        return short_hash
        
    for f in os.listdir(commits_dir):
        if f.startswith(short_hash) and f.endswith(".json"):
            return f.replace(".json", "")
    return short_hash

@cli.command()
@click.argument('hash1')
@click.argument('hash2', required=False)
@click.option('--schema-only', is_flag=True)
@click.option('--data-only', is_flag=True)
def diff(hash1, hash2, schema_only, data_only):
    """Compare two commits or HEAD with a commit."""
    try:
        path = get_db_path(None)
        h1 = resolve_hash(hash1, path)
        h2 = resolve_hash(hash2, path) if hash2 else None
        
        if not h2:
            head = load_commit(path)
            if not head:
                console.print("[red]Error: HEAD not found.[/red]")
                return
            h2 = head.hash
            
        s_diff, d_diff = gitdb_diff(h1, h2, path)
    except Exception as e:
        console.print(f"[red]Diff failed: {e}[/red]")

@cli.command()
@click.argument('target_hash')
def checkout(target_hash):
    """Restore the database to a specific commit."""
    try:
        path = get_db_path(None)
        full_hash = resolve_hash(target_hash, path)
        gitdb_checkout(full_hash, path)
        console.print(f"[bold green]Successfully checked out to {full_hash[:8]}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Checkout failed:[/bold red] {e}")

@cli.command()
def status():
    """Show the current HEAD commit."""
    try:
        path = get_db_path(None)
        commit = load_commit(path)
        if commit:
            console.print(f"On branch [bold blue]main[/bold blue]")
            console.print(f"Current HEAD: [bold yellow]{commit.hash}[/bold yellow]")
            console.print(f"Message: {commit.message}")
        else:
            console.print("No commits yet. Use 'gitdb commit -m \"msg\"' to create one.")
    except Exception as e:
        console.print(f"[red]Status failed: {e}[/red]")

if __name__ == '__main__':
    cli()
