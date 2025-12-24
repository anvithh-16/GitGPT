import subprocess
import os
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

def confirm_and_execute(command_data: dict):
    """
    Displays the command, warning, explanation, and next-step guidance.
    Asks for confirmation unless the 'auto_execute' flag is true.
    """
    command = command_data.get("command")
    explanation = command_data.get("explanation")
    warning = command_data.get("ambiguity_warning")
    next_step = command_data.get("next_step_suggestion")
    auto_execute = command_data.get("auto_execute", False) 
    
    if not command:
        console.print("[bold red]Error: No command was generated.[/bold red]")
        return

    # --- Display the results ---
    if warning:
        # Check if the warning is a DANGER warning and style accordingly
        if warning.startswith("DANGER:"):
            title = "[bold red]DANGER WARNING[/bold red]"
            style = "red"
        else:
            title = "[bold yellow]Warning[/bold yellow]"
            style = "yellow"
        
        console.print(Panel(warning, title=title, border_style=style))

    # Cosmetic change: Use a different title/color if it is a chained command (contains '&&')
    if " && " in command:
        title = "[bold magenta]Generated Chained Command[/bold magenta]"
        style = "magenta"
    else:
        title = "[bold green]Generated Command[/bold green]"
        style = "green"
        
    console.print(Panel(command, title=title, border_style=style))
    
    # --- Display the explanation right after the command ---
    if explanation:
        console.print(Panel(
            Text(explanation, justify="left"),
            title="[bold cyan]💡 Command Explanation[/bold cyan]",
            border_style="cyan",
            padding=(0, 1)
        ))
    # -------------------------------------------------------------
    
    # --- Ask for confirmation ---
    confirm = False
    
    if auto_execute:
        console.print("[bold blue]✅ Auto-executing command based on your affirmative response.[/bold blue]")
        confirm = True
    else:
        try:
            # If not auto-execute, ask for explicit confirmation
            confirm = questionary.confirm("Do you want to execute this command?").ask()
        except KeyboardInterrupt:
            console.print("\n[bold red]Operation cancelled.[/bold red]")
            return

    # --- Execute if confirmed ---
    if confirm:
        console.print(f"\n[bold]Executing: {command}[/bold]\n")
        try:
            # Using subprocess.run with shell=True to execute the command string
            process = subprocess.Popen(
                command, 
                shell=True, 
                text=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT
            )
            
            # Read and print output line by line
            for line in iter(process.stdout.readline, ''):
                print(line, end='')
            
            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                console.print(f"\n[bold green]Command successful![/bold green]")
                
                # --- Display the conversational next step suggestion ---
                if next_step:
                    console.print(Panel(
                        Text(next_step), 
                        title="[bold blue]🚀 What's Next?[/bold blue]", 
                        border_style="blue"
                    ))
            else:
                console.print(f"\n[bold red]Command finished with exit code {return_code}[/bold red]")

        except Exception as e:
            console.print(f"[bold red]An error occurred during execution: {e}[/bold red]")
    else:
        console.print("[bold yellow]Execution cancelled.[/bold yellow]")


def resolve_conflict(conflict_block: dict, resolution: dict):
    """
    Displays the conflict resolution and asks for confirmation.
    """
    file_path = conflict_block.get("file_path")
    start_line = conflict_block.get("start_line")
    current_content = conflict_block.get("current_content")
    incoming_content = conflict_block.get("incoming_content")
    
    suggestion = resolution.get("suggestion")
    merged_content = resolution.get("merged_content")
    explanation = resolution.get("explanation")
    confidence = resolution.get("confidence")
    reasoning = resolution.get("reasoning")

    if not merged_content:
        console.print("[bold red]Error: No resolution was generated.[/bold red]")
        return False

    # --- Display the conflict ---
    console.print(f"\n{'='*60}")
    console.print(f"[bold cyan]Conflict in {file_path}[/bold cyan] (line {start_line + 1})")
    console.print('='*60)
    
    console.print(Panel(explanation, title="[bold blue]What Changed[/bold blue]", border_style="blue"))
    
    console.print("\n[bold red]YOUR version (current branch):[/bold red]")
    console.print(current_content.rstrip())
    
    console.print("\n[bold yellow]THEIR version (incoming branch):[/bold yellow]")
    console.print(incoming_content.rstrip())
    
    # Show AI suggestion
    confidence_colors = {
        "HIGH": "green",
        "MEDIUM": "yellow",
        "LOW": "red"
    }
    color = confidence_colors.get(confidence, "white")
    
    console.print(f"\n[bold]AI Suggestion:[/bold] [{color}]{suggestion.upper().replace('_', ' ')}[/{color}]")
    console.print(f"[bold]Confidence:[/bold] [{color}]{confidence}[/{color}]")
    console.print(Panel(reasoning, title=f"[bold {color}]Reasoning[/bold {color}]", border_style=color))
    
    console.print("\n[bold green]Proposed Resolution:[/bold green]")
    console.print(merged_content.rstrip())
    console.print()
    
    # --- Ask for confirmation ---
    try:
        choice = questionary.select(
            "Do you want to apply this resolution?",
            choices=[
                "Accept AI suggestion",
                "Keep YOUR version",
                "Keep THEIR version",
                "Skip for now",
                "Cancel"
            ]
        ).ask()
    except KeyboardInterrupt:
        console.print("\n[bold red]Operation cancelled.[/bold red]")
        return False

    # --- Apply resolution ---
    if choice == "Cancel":
        console.print("[bold yellow]Execution cancelled.[/bold yellow]")
        return False
    
    if choice == "Skip for now":
        console.print("[yellow]Skipped[/yellow]")
        return False
    
    # Determine what content to use
    content_to_apply = merged_content
    if choice == "Keep YOUR version":
        content_to_apply = current_content
    elif choice == "Keep THEIR version":
        content_to_apply = incoming_content
    
    # Apply the resolution
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Ensure content ends with newline
        if content_to_apply and not content_to_apply.endswith('\n'):
            content_to_apply += '\n'
        
        # Replace the conflict block
        end_line = conflict_block.get("end_line")
        new_lines = (
            lines[:start_line] +
            [content_to_apply] +
            lines[end_line + 1:]
        )
        
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.writelines(new_lines)
        
        console.print("[green]✓ Resolution applied[/green]")
        return True
        
    except Exception as e:
        console.print(f"[bold red]Error applying resolution: {e}[/bold red]")
        return False