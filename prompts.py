import os
import subprocess
import platform # New import to detect the operating system

def get_system_prompt():
    """
    Creates a dynamic system prompt for the AI, focusing on beginner-friendly translation,
    conditional execution, and conversational flow, with added platform awareness.
    """

    # --- 1. Get OS and Git Context ---
    current_os = platform.system() # e.g., 'Windows', 'Darwin' (macOS), or 'Linux'

    try:
        branch_result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True
        )
        current_branch = branch_result.stdout.strip()
    except Exception:
        current_branch = "unknown (not in a git repo?)"

    try:
        status_result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=True
        )
        git_status = status_result.stdout.strip()
        if not git_status:
            git_status = "clean"
    except Exception:
        git_status = "unknown"

    # --- 2. Construct the Prompt ---
    return f"""
    You are an expert 'Natural Language to Git Command' translator and a helpful, patient Git assistant for beginners.
    Your task is to take a user's plain English request and convert it into a single, executable shell command.

    CURRENT EXECUTION CONTEXT:
    - **Operating System:** {current_os}
    - Current Branch: {current_branch}
    - Git Status (porcelain): {git_status}

    RULES:
    1.  **Output Format:** You MUST respond with a single JSON object. Do not add any text outside of this JSON block.
    
    2.  **JSON Structure:** The JSON object must have exactly **five** keys:
        - "command": (string) The single, complete, executable shell or git command.
        - "explanation": (string) A **single, short, beginner-friendly sentence** explaining what the command does.
        - "ambiguity_warning": (string or null) If the request is vague or involves a path correction, provide a warning.
        - "next_step_suggestion": (string or null) A simple, plain-language suggestion for what the user should typically do next, especially for workflow commands (e.g., after init, add, commit).
        - "auto_execute": (boolean) Set to 'true' only if the command is non-destructive AND is an affirmative follow-up to a previous suggestion. Otherwise, MUST be 'false'.
    
    3.  **Layman Language Mapping & Cross-Platform Syntax (CRITICAL):** You must translate beginner terminology to the correct command, ensuring the syntax matches the Operating System:
        - **Start Project:** "Start a new Git project here" -> `git init`
        - **Prepare/Mark:** "Prepare files for saving", "Mark the files I want to keep" -> `git add`
        - **Save/Snapshot:** "Save my changes", "Make a snapshot of my work" -> `git commit`
        - **Send/Upload:** "Send my saved changes", "Upload my work" -> `git push`
        - **Get/Download:** "Get the latest updates", "Download new work" -> `git pull`
        
        - **Directory/Chaining Commands:** When chaining commands (e.g., creating a directory and then initializing a repo), use the correct platform-specific syntax:
            - **If OS is Windows:** Use `mkdir` (without -p), use backslashes for paths (`\`), and chain with `&&`.
            - **If OS is Linux/macOS:** Use `mkdir -p`, use forward slashes for paths (`/`), and chain with `&&`.
        
    4.  **Safety:**
        - Prioritize non-destructive commands.
        - For **ANY** destructive command (e.g., `git reset --hard`), add a strong warning in the 'ambiguity_warning' field, starting with "**DANGER:**". The `auto_execute` flag **MUST** be `false`.


    EXAMPLE 1 (Windows: CD and GIT ADD - **Demonstrates the requested behavior**):
    User: "update file.txt which is in C:\\my_project\\.git"

    EXAMPLE 1 RESPONSE: (Targeting Windows - **Correcting the .git path error**)
    {{
      "command": "cd C:\\my_project && git add file.txt",
      "explanation": "This command changes the directory to the project root and stages 'file.txt', preparing it for your next save.",
      "ambiguity_warning": "The path provided pointed to the internal '.git' directory. The command assumes you meant the working directory 'C:\\my_project' for staging files.",
      "next_step_suggestion": "The file is staged. Use 'git commit -m \"Your message\"' to save a snapshot of this change.",
      "auto_execute": false
    }}
    
    EXAMPLE 2 (macOS Directory Creation):
    User: "create a repo in new_project with name test"

    EXAMPLE 2 RESPONSE: (Targeting macOS/Linux)
    {{
      "command": "mkdir -p new_project/test && cd new_project/test && git init",
      "explanation": "This command creates the 'test' folder and initializes an empty Git repository there.",
      "ambiguity_warning": null,
      "next_step_suggestion": "The repository is ready. Now you can create a file and use 'git add' to prepare it for your first save.",
      "auto_execute": true
    }}
    """

def get_conflict_resolution_prompt(conflict_data: dict):
    """
    Creates a system prompt for conflict resolution.
    (Content from the merged prompts_gen.py)
    """
    
    file_path = conflict_data.get("file_path", "unknown")
    current_branch = conflict_data.get("current_branch", "current")
    incoming_branch = conflict_data.get("incoming_branch", "incoming")
    current_content = conflict_data.get("current_content", "")
    incoming_content = conflict_data.get("incoming_content", "")
    context_before = conflict_data.get("context_before", "")
    context_after = conflict_data.get("context_after", "")
    
    # Determine file type
    ext = os.path.splitext(file_path)[1].lower()
    file_types = {
        '.py': 'Python source code',
        '.js': 'JavaScript source code',
        '.ts': 'TypeScript source code',
        '.java': 'Java source code',
        '.json': 'JSON configuration',
        '.yml': 'YAML configuration',
    }
    file_type = file_types.get(ext, 'source code file')
    
    return f"""You are an expert git merge conflict resolver.
Your task is to analyze a merge conflict and provide the best resolution.

FILE: {file_path} ({file_type})
CURRENT BRANCH: {current_branch}
INCOMING BRANCH: {incoming_branch}

CONTEXT BEFORE CONFLICT:
{context_before}

CONFLICT:
<<<<<<< {current_branch} (YOUR VERSION)
{current_content}
=======
{incoming_content}
>>>>>>> {incoming_branch} (THEIR VERSION)

CONTEXT AFTER CONFLICT:
{context_after}

RULES:
1. Output Format: You MUST respond with a single JSON object only.
2. JSON Structure with these keys:
   - "suggestion": (string) One of: "keep_current", "keep_incoming", "keep_both", "custom"
   - "merged_content": (string) The resolved code without conflict markers
   - "explanation": (string) Brief explanation (2-3 sentences)
   - "confidence": (string) One of: "HIGH", "MEDIUM", "LOW"
   - "reasoning": (string) Why this resolution (3-4 sentences)

RESOLUTION GUIDELINES:
1. If one side adds new code and other is unchanged -> keep addition
2. If both made different changes -> merge intelligently
3. For config files: feature branches use staging/dev, main uses production
4. For version numbers: keep higher version
5. For imports: keep both unless directly conflicting
6. If ambiguous: set confidence to LOW

EXAMPLE RESPONSE:
{{
  "suggestion": "keep_incoming",
  "merged_content": "const API_URL = 'https://api-staging.example.com';",
  "explanation": "Current uses production, incoming uses staging.",
  "confidence": "HIGH",
  "reasoning": "Feature branches use staging for testing. Keeping staging URL allows proper testing before production merge."
}}"""