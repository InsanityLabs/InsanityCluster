"""
CLI interface for command submission to Insanity Cluster.

Provides a command-line interface for submitting natural language commands,
viewing task status, and streaming realtime progress updates.
"""
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime

import click
import httpx
import websockets
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.markdown import Markdown

# Setup logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()


class InsanityClusterCLI:
    """CLI client for Insanity Cluster"""
    
    def __init__(self, api_url: str, api_key: Optional[str] = None):
        """
        Initialize CLI client.
        
        Args:
            api_url: Base URL for API
            api_key: API key for authentication
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.headers = {}
        
        if self.api_key:
            self.headers["X-API-Key"] = self.api_key
    
    async def submit_command(self, command: str, priority: int = 1) -> Optional[str]:
        """
        Submit a command to the API.
        
        Args:
            command: Natural language command
            priority: Task priority (1-5)
            
        Returns:
            Task ID if successful
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/tasks",
                    json={
                        "command": command,
                        "priority": priority
                    },
                    headers=self.headers,
                    timeout=30.0
                )
                
                if response.status_code == 201:
                    data = response.json()
                    return data["task_id"]
                else:
                    console.print(f"[red]Error: {response.status_code}[/red]")
                    console.print(response.text)
                    return None
                    
        except Exception as e:
            console.print(f"[red]Failed to submit command: {e}[/red]")
            return None
    
    async def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        Get task status from API.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task status data
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/tasks/{task_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    console.print(f"[red]Error: {response.status_code}[/red]")
                    return None
                    
        except Exception as e:
            console.print(f"[red]Failed to get task status: {e}[/red]")
            return None
    
    async def list_tasks(self, status_filter: Optional[str] = None, limit: int = 10) -> Optional[list]:
        """
        List tasks from API.
        
        Args:
            status_filter: Optional status filter
            limit: Maximum number of tasks
            
        Returns:
            List of tasks
        """
        try:
            params = {"limit": limit}
            if status_filter:
                params["status_filter"] = status_filter
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/tasks",
                    params=params,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    console.print(f"[red]Error: {response.status_code}[/red]")
                    return None
                    
        except Exception as e:
            console.print(f"[red]Failed to list tasks: {e}[/red]")
            return None
    
    async def stream_task_updates(self, task_id: str):
        """
        Stream realtime task updates via WebSocket.
        
        Args:
            task_id: Task ID to monitor
        """
        ws_url = self.api_url.replace("http://", "ws://").replace("https://", "wss://")
        ws_url = f"{ws_url}/ws?token={self.api_key}"
        
        try:
            async with websockets.connect(ws_url) as websocket:
                # Subscribe to task updates
                await websocket.send(json.dumps({
                    "type": "subscribe",
                    "task_id": task_id
                }))
                
                console.print(f"[green]Streaming updates for task {task_id}...[/green]")
                
                # Receive updates
                async for message in websocket:
                    data = json.loads(message)
                    
                    if data["type"] == "task_update":
                        self._display_task_update(data)
                        
                        # Stop if task completed
                        if data["status"] in ["completed", "failed", "cancelled"]:
                            break
                    
                    elif data["type"] == "ping":
                        # Respond to heartbeat
                        await websocket.send(json.dumps({"type": "pong"}))
                    
        except Exception as e:
            console.print(f"[red]WebSocket error: {e}[/red]")
    
    def _display_task_update(self, update: dict):
        """Display task update"""
        status = update["status"]
        progress = update.get("progress", 0.0)
        message = update["message"]
        
        # Color based on status
        color = "yellow"
        if status == "completed":
            color = "green"
        elif status == "failed":
            color = "red"
        
        console.print(f"[{color}]{status.upper()}[/{color}] ({progress*100:.0f}%) - {message}")


# CLI Commands
@click.group()
@click.option("--api-url", envvar="INSANITY_API_URL", default="http://localhost:8000", help="API URL")
@click.option("--api-key", envvar="INSANITY_API_KEY", help="API key")
@click.pass_context
def cli(ctx, api_url, api_key):
    """Insanity Cluster CLI - Multi-modal AI orchestration system"""
    ctx.ensure_object(dict)
    ctx.obj["client"] = InsanityClusterCLI(api_url, api_key)


@cli.command()
@click.argument("command", nargs=-1, required=True)
@click.option("--priority", default=1, type=click.IntRange(1, 5), help="Task priority (1-5)")
@click.option("--stream", is_flag=True, help="Stream realtime updates")
@click.pass_context
def run(ctx, command, priority, stream):
    """Submit a command for execution"""
    client = ctx.obj["client"]
    command_text = " ".join(command)
    
    console.print(Panel(f"[bold]Command:[/bold] {command_text}", title="Submitting Task"))
    
    # Submit command
    task_id = asyncio.run(client.submit_command(command_text, priority))
    
    if not task_id:
        sys.exit(1)
    
    console.print(f"[green]✓[/green] Task created: [bold]{task_id}[/bold]")
    
    # Stream updates if requested
    if stream:
        asyncio.run(client.stream_task_updates(task_id))
    else:
        console.print(f"\nUse [bold]ic status {task_id}[/bold] to check progress")


@cli.command()
@click.argument("task_id")
@click.option("--stream", is_flag=True, help="Stream realtime updates")
@click.pass_context
def status(ctx, task_id, stream):
    """Get status of a task"""
    client = ctx.obj["client"]
    
    if stream:
        # Stream updates
        asyncio.run(client.stream_task_updates(task_id))
    else:
        # Get current status
        task_data = asyncio.run(client.get_task_status(task_id))
        
        if not task_data:
            sys.exit(1)
        
        # Display status
        table = Table(title=f"Task Status: {task_id}")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Status", task_data["status"])
        table.add_row("Command", task_data["command"])
        table.add_row("Cost", f"${task_data['cost']:.4f}")
        
        if task_data.get("latency_ms"):
            table.add_row("Latency", f"{task_data['latency_ms']}ms")
        
        table.add_row("Created", task_data["created_at"])
        
        if task_data.get("completed_at"):
            table.add_row("Completed", task_data["completed_at"])
        
        console.print(table)
        
        # Display result if completed
        if task_data.get("result"):
            console.print("\n[bold]Result:[/bold]")
            console.print(json.dumps(task_data["result"], indent=2))


@cli.command()
@click.option("--status-filter", help="Filter by status")
@click.option("--limit", default=10, help="Maximum number of tasks")
@click.pass_context
def list(ctx, status_filter, limit):
    """List recent tasks"""
    client = ctx.obj["client"]
    
    tasks = asyncio.run(client.list_tasks(status_filter, limit))
    
    if not tasks:
        console.print("[yellow]No tasks found[/yellow]")
        return
    
    # Display tasks table
    table = Table(title="Recent Tasks")
    table.add_column("Task ID", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Command", style="white", max_width=50)
    table.add_column("Cost", style="green")
    table.add_column("Created", style="white")
    
    for task in tasks:
        status_color = "yellow"
        if task["status"] == "completed":
            status_color = "green"
        elif task["status"] == "failed":
            status_color = "red"
        
        table.add_row(
            task["task_id"][:8] + "...",
            f"[{status_color}]{task['status']}[/{status_color}]",
            task["command"][:50] + "..." if len(task["command"]) > 50 else task["command"],
            f"${task['cost']:.4f}",
            task["created_at"]
        )
    
    console.print(table)


@cli.command()
@click.pass_context
def config(ctx):
    """Show current configuration"""
    client = ctx.obj["client"]
    
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("API URL", client.api_url)
    table.add_row("API Key", "***" + client.api_key[-8:] if client.api_key else "[red]Not set[/red]")
    
    console.print(table)
    
    # Check connection
    console.print("\n[bold]Testing connection...[/bold]")
    try:
        response = httpx.get(f"{client.api_url}/health", timeout=5.0)
        if response.status_code == 200:
            console.print("[green]✓[/green] API is reachable")
        else:
            console.print(f"[red]✗[/red] API returned status {response.status_code}")
    except Exception as e:
        console.print(f"[red]✗[/red] Cannot reach API: {e}")


@cli.command()
def setup():
    """Setup CLI configuration"""
    console.print("[bold]Insanity Cluster CLI Setup[/bold]\n")
    
    # Get API URL
    api_url = click.prompt(
        "API URL",
        default="http://localhost:8000"
    )
    
    # Get API key
    api_key = click.prompt(
        "API Key",
        hide_input=True
    )
    
    # Save to config file
    config_dir = Path.home() / ".insanity_cluster"
    config_dir.mkdir(exist_ok=True)
    
    config_file = config_dir / "config.json"
    config_data = {
        "api_url": api_url,
        "api_key": api_key
    }
    
    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)
    
    console.print(f"\n[green]✓[/green] Configuration saved to {config_file}")
    console.print("\nYou can also set environment variables:")
    console.print("  export INSANITY_API_URL=<url>")
    console.print("  export INSANITY_API_KEY=<key>")


@cli.command()
@click.pass_context
def interactive(ctx):
    """Start interactive mode"""
    client = ctx.obj["client"]
    
    console.print(Panel(
        "[bold]Insanity Cluster Interactive Mode[/bold]\n\n"
        "Type your commands in natural language.\n"
        "Type 'exit' or 'quit' to leave.\n"
        "Type 'help' for available commands.",
        title="Welcome"
    ))
    
    while True:
        try:
            # Get command
            command = click.prompt("\n[bold cyan]>[/bold cyan]", prompt_suffix=" ")
            
            if command.lower() in ["exit", "quit"]:
                console.print("[yellow]Goodbye![/yellow]")
                break
            
            if command.lower() == "help":
                console.print("""
[bold]Available commands:[/bold]
  - Any natural language command (e.g., "Create a Python web scraper")
  - list - Show recent tasks
  - status <task_id> - Check task status
  - exit/quit - Exit interactive mode
                """)
                continue
            
            if command.lower() == "list":
                tasks = asyncio.run(client.list_tasks(limit=5))
                if tasks:
                    for task in tasks:
                        console.print(f"  {task['task_id'][:8]}... - {task['status']} - {task['command'][:50]}")
                continue
            
            if command.lower().startswith("status "):
                task_id = command.split()[1]
                task_data = asyncio.run(client.get_task_status(task_id))
                if task_data:
                    console.print(f"Status: {task_data['status']}")
                    console.print(f"Command: {task_data['command']}")
                continue
            
            # Submit command
            task_id = asyncio.run(client.submit_command(command))
            if task_id:
                console.print(f"[green]✓[/green] Task created: {task_id}")
                console.print("Streaming updates...")
                asyncio.run(client.stream_task_updates(task_id))
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Interrupted[/yellow]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


if __name__ == "__main__":
    cli()
