import argparse
import sys
import os
import subprocess
from rich.console import Console
from rich.spinner import Spinner

# Import both API functions and both executor functions
from .api_client import get_git_command, get_conflict_resolution
from .executor import confirm_and_execute, resolve_conflict

console = Console()

# --- Functions copied from main_gen.py for conflict resolution ---

def get_conflicted_files():
    """Get list of files with merge conflicts."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            capture_output=True, text=True, check=True
        )
        files = [f.strip() for f in result.stdout.split('\n') if f.strip()]
        return files
    except:
        return []

def parse_conflict_file(file_path):
    """Parse a file and extract conflict blocks."""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        console.print(f"[bold red]Error reading {file_path}: {e}[/bold red]")
        return []
    
    conflicts = []
    i = 0
    
    while i < len(lines):
        if lines[i].startswith('<<<<<<<'):
            conflict_start = i
            current_lines = []
            incoming_lines = []
            
            context_before = ''.join(lines[max(0, i-5):i])
            
            i += 1
            while i < len(lines) and not lines[i].startswith('======='):
                current_lines.append(lines[i])
                i += 1
            
            i += 1  # Skip =======
            
            while i < len(lines) and not lines[i].startswith('>>>>>>>'):
                incoming_lines.append(lines[i])
                i += 1
            
            context_after = ''.join(lines[i+1:min(len(lines), i+6)])
            
            conflicts.append({
                "file_path": file_path,
                "start_line": conflict_start,
                "end_line": i,
                "current_content": ''.join(current_lines),
                "incoming_content": ''.join(incoming_lines),
                "context_before": context_before,
                "context_after": context_after
            })
        i += 1
    
    return conflicts

def get_branch_info():
    """Get current and incoming branch names."""
    try:
        current = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        ).stdout.strip()
        
        # Use os.path.join for cross-platform path creation
        merge_msg_path = os.path.join(".git", "MERGE_HEAD")
        if os.path.exists(merge_msg_path):
            with open(merge_msg_path, 'r') as f:
                merge_sha = f.read().strip()
            try:
                merge_branch = subprocess.run(
                    ["git", "name-rev", "--name-only", merge_sha],
                    capture_output=True, text=True, check=True
                ).stdout.strip()
            except:
                merge_branch = "incoming-branch"
        else:
            merge_branch = "incoming-branch"
        
        return {"current": current, "incoming": merge_branch}
    except:
        return {"current": "current-branch", "incoming": "incoming-branch"}

def handle_conflict_resolution():
    """Handle conflict resolution mode."""
    console.print("\n[bold green]Git AI Conflict Resolver[/bold green]")
    console.print("[dim]Powered by Gemini AI[/dim]\n")
    
    # Check if in git repo
    try:
        subprocess.run(["git", "rev-parse", "--git-dir"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        console.print("[bold red]Error: Not in a git repository![/bold red]")
        return
    
    branch_info = get_branch_info()
    console.print(f"Current branch: [cyan]{branch_info['current']}[/cyan]")
    console.print(f"Merging from: [cyan]{branch_info['incoming']}[/cyan]\n")
    
    conflicted_files = get_conflicted_files()
    
    if not conflicted_files:
        console.print("[green]No conflicts found![/green]")
        return
    
    console.print(f"Found [yellow]{len(conflicted_files)}[/yellow] conflicted file(s)\n")
    
    total_conflicts = 0
    resolved_count = 0
    
    for file_path in conflicted_files:
        conflicts = parse_conflict_file(file_path)
        
        if not conflicts:
            continue
        
        console.print(f"\n[bold cyan]Processing {file_path}[/bold cyan]: {len(conflicts)} conflict(s)")
        total_conflicts += len(conflicts)
        
        for idx, conflict in enumerate(conflicts, 1):
            console.print(f"\n[bold]Conflict {idx}/{len(conflicts)}[/bold]")
            
            # Add branch info to conflict data
            conflict["current_branch"] = branch_info["current"]
            conflict["incoming_branch"] = branch_info["incoming"]
            
            # Get AI resolution
            with console.status("[bold green]Asking the AI...", spinner="dots"):
                resolution = get_conflict_resolution(conflict)
            
            if not resolution:
                console.print("[bold red]Failed to get resolution. Skipping.[/bold red]")
                continue
            
            # Let user decide what to do
            if resolve_conflict(conflict, resolution):
                resolved_count += 1
    
    # Summary
    console.print(f"\n{'='*60}")
    console.print("[bold green]Resolution complete![/bold green]")
    console.print(f"Resolved: {resolved_count}/{total_conflicts} conflicts")
    console.print('='*60)
    
    if resolved_count > 0:
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Review: [cyan]git diff[/cyan]")
        console.print("  2. Stage: [cyan]git add .[/cyan]")
        console.print("  3. Commit: [cyan]git commit[/cyan]")

# --- Main CLI Function ---

def run_cli():
    """
    The main CLI entry function, dispatching to command translation or conflict resolution.
    """
    parser = argparse.ArgumentParser(
        description="Translate natural language to Git commands OR resolve merge conflicts with AI."
    )
    parser.add_argument(
        "query",
        type=str,
        nargs="*",
        help="Natural language query (e.g., 'show me my last 3 commits') OR 'resolve' to fix conflicts."
    )
    
    if len(sys.argv) == 1:
        # No arguments - check for conflicts
        conflicted_files = get_conflicted_files()
        if conflicted_files:
            console.print("\n[bold yellow]⚠️  Merge conflicts detected![/bold yellow]")
            console.print(f"Found {len(conflicted_files)} conflicted file(s):\n")
            for f in conflicted_files:
                console.print(f"  • {f}")
            console.print("\n[bold]Run with 'resolve' to fix them:[/bold]")
            console.print("  [cyan]python run.py resolve[/cyan]\n")
        else:
            parser.print_help(sys.stderr)
        sys.exit(1)

    args = parser.parse_args()
    
    # Check if user wants to resolve conflicts
    if args.query and args.query[0].lower() == "resolve":
        handle_conflict_resolution()
        return
    
    # Otherwise, treat as normal command translation
    user_query = " ".join(args.query)

    # Show a spinner while waiting for the API
    with console.status("[bold green]Asking the AI...", spinner="dots") as status:
        try:
            command_data = get_git_command(user_query)
        except Exception as e:
            console.print(f"\n[bold red]An unexpected error occurred: {e}[/bold red]")
            sys.exit(1)

    if command_data:
        confirm_and_execute(command_data)
    else:
        console.print("[bold red]Failed to get a valid command from the AI.[/bold red]")

if __name__ == "__main__":
    run_cli()