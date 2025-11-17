#!/usr/bin/env python3
"""
Example CLI Application using Insanity Cluster

This example demonstrates how to build a command-line application
that interacts with Insanity Cluster to execute tasks.

Usage:
    python cli_example.py "Write a Python function to calculate fibonacci"
    python cli_example.py --config config.yaml "Your command here"
    python cli_example.py --stream "Generate a story about AI"
"""

import asyncio
import argparse
import sys
import json
from typing import Optional
import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

console = Console()

class InsanityClusterClient:
    """Client for interacting with Insanity Cluster API"""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"X-API-Key": api_key},
            timeout=300.0
        )
    
    async def create_task(self, command: str, priority: str = "normal") -> dict:
        """Create a new task"""
        response = await self.client.post(
            "/tasks",
            json={"command": command, "priority": priority}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_task_status(self, task_id: str) -> dict:
        """Get task status"""
        response = await self.client.get(f"/tasks/{task_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_task_result(self, task_id: str) -> dict:
        """Get task result"""
        response = await self.client.get(f"/tasks/{task_id}/result")
        response.raise_for_status()
        return response.json()
    
    async def wait_for_completion(
        self,
        task_id: str,
        timeout: int = 300,
        poll_interval: int = 2
    ) -> dict:
        """Wait for task to complete"""
        elapsed = 0
        
        while elapsed < timeout:
            status = await self.get_task_status(task_id)
            
            if status["status"] in ["completed", "failed", "cancelled"]:
                return status
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()


async def execute_task_simple(client: InsanityClusterClient, command: str):
    """Execute a task and wait for completion (simple version)"""
    console.print(f"[bold blue]Creating task:[/bold blue] {command}")
    
    # Create task
    task = await client.create_task(command)
    task_id = task["task_id"]
    
    console.print(f"[green]Task created:[/green] {task_id}")
    console.print(f"[yellow]Status:[/yellow] {task['status']}")
    
    # Wait for completion with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task_progress = progress.add_task("Executing task...", total=None)
        
        try:
            result = await client.wait_for_completion(task_id)
            progress.update(task_progress, completed=True)
        except TimeoutError as e:
            console.print(f"[red]Error:[/red] {e}")
            return
    
    # Display result
    if result["status"] == "completed":
        console.print("[bold green]✓ Task completed successfully![/bold green]")
        
        # Get full result
        full_result = await client.get_task_result(task_id)
        
        # Display result in a panel
        result_text = json.dumps(full_result["result"], indent=2)
        console.print(Panel(result_text, title="Result", border_style="green"))
        
        # Display metrics
        metrics = full_result.get("metrics", {})
        table = Table(title="Metrics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Cost", f"${metrics.get('total_cost', 0):.4f}")
        table.add_row("Latency", f"{metrics.get('total_latency_ms', 0)}ms")
        table.add_row("Models Used", ", ".join(metrics.get('models_used', [])))
        
        console.print(table)
    
    elif result["status"] == "failed":
        console.print("[bold red]✗ Task failed[/bold red]")
        console.print(f"[red]Error:[/red] {result.get('error', 'Unknown error')}")
    
    else:
        console.print(f"[yellow]Task status:[/yellow] {result['status']}")


async def execute_task_with_updates(client: InsanityClusterClient, command: str):
    """Execute a task with real-time updates via polling"""
    console.print(f"[bold blue]Creating task:[/bold blue] {command}")
    
    # Create task
    task = await client.create_task(command)
    task_id = task["task_id"]
    
    console.print(f"[green]Task created:[/green] {task_id}")
    
    # Create live display for updates
    table = Table(title="Task Progress")
    table.add_column("Status", style="cyan")
    table.add_column("Progress", style="magenta")
    table.add_column("Active Agents", style="green")
    table.add_column("Cost", style="yellow")
    
    with Live(table, refresh_per_second=2, console=console) as live:
        while True:
            status = await client.get_task_status(task_id)
            
            # Update table
            table = Table(title="Task Progress")
            table.add_column("Status", style="cyan")
            table.add_column("Progress", style="magenta")
            table.add_column("Active Agents", style="green")
            table.add_column("Cost", style="yellow")
            
            progress = status.get("progress", {})
            percentage = progress.get("percentage", 0)
            active_agents = ", ".join(status.get("active_agents", []))
            cost = status.get("cost_so_far", 0)
            
            table.add_row(
                status["status"],
                f"{percentage:.1f}%",
                active_agents or "None",
                f"${cost:.4f}"
            )
            
            live.update(table)
            
            # Check if complete
            if status["status"] in ["completed", "failed", "cancelled"]:
                break
            
            await asyncio.sleep(2)
    
    # Display final result
    if status["status"] == "completed":
        console.print("[bold green]✓ Task completed successfully![/bold green]")
        
        full_result = await client.get_task_result(task_id)
        result_text = json.dumps(full_result["result"], indent=2)
        console.print(Panel(result_text, title="Result", border_style="green"))
    
    elif status["status"] == "failed":
        console.print("[bold red]✗ Task failed[/bold red]")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Insanity Cluster CLI Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli_example.py "Write a Python function"
  python cli_example.py --api-key YOUR_KEY "Your command"
  python cli_example.py --updates "Generate a story"
        """
    )
    
    parser.add_argument(
        "command",
        help="Command to execute"
    )
    
    parser.add_argument(
        "--api-key",
        default="ic_test_demo",
        help="API key for authentication"
    )
    
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000/v1",
        help="Base URL for Insanity Cluster API"
    )
    
    parser.add_argument(
        "--priority",
        choices=["low", "normal", "high", "urgent"],
        default="normal",
        help="Task priority"
    )
    
    parser.add_argument(
        "--updates",
        action="store_true",
        help="Show real-time updates"
    )
    
    args = parser.parse_args()
    
    # Create client
    client = InsanityClusterClient(args.api_key, args.base_url)
    
    try:
        if args.updates:
            await execute_task_with_updates(client, args.command)
        else:
            await execute_task_simple(client, args.command)
    
    except httpx.HTTPStatusError as e:
        console.print(f"[red]HTTP Error:[/red] {e.response.status_code}")
        console.print(f"[red]Message:[/red] {e.response.text}")
        sys.exit(1)
    
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)
    
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
