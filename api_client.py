import os
import json
import warnings
import google.generativeai as genai
from dotenv import load_dotenv
from rich.console import Console

from .prompts import get_system_prompt, get_conflict_resolution_prompt

# --- Warning Suppression ---
# Filter out FutureWarnings (for Python 3.9 deprecation) and specific 
# NotOpenSSLWarning (for urllib3/LibreSSL conflicts)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", "urllib3 v2 only supports OpenSSL 1.1.1+", category=UserWarning)
# ---------------------------

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

console = Console()

def get_git_command(user_query: str):
    """
    Sends the user query to the Gemini API and gets a git command.
    """
    if not API_KEY:
        console.print("[bold red]Error: GEMINI_API_KEY not found.[/bold red]")
        console.print("Please add your key to a `.env` file in the project root.")
        return None

    try:
        # Configure the client
        genai.configure(api_key=API_KEY)

        # Set up generation config
        generation_config = {
            # Low temperature for deterministic code generation
            "temperature": 0.0, 
            # Critical: Ensures the output is a valid JSON string
            "response_mime_type": "application/json",
        }
        
        system_prompt = get_system_prompt()

        # Initialize the model
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash", 
            generation_config=generation_config,
            system_instruction=system_prompt
        )

        # Send the prompt
        response = model.generate_content(user_query)
        
        # The response.text will now be a perfect, valid JSON string
        response_text = response.text.strip()
        return json.loads(response_text)

    except json.JSONDecodeError:
        console.print("[bold red]Error: Failed to decode AI response. Is the model adhering to the JSON schema?[/bold red]")
        console.print(f"Raw response: {response_text}")
        return None
    except Exception as e:
        console.print(f"[bold red]An API error occurred: {e}[/bold red]")
        return None


def get_conflict_resolution(conflict_data: dict):
    """
    Sends conflict data to the Gemini API and gets a resolution suggestion.
    """
    if not API_KEY:
        console.print("[bold red]Error: GEMINI_API_KEY not found.[/bold red]")
        console.print("Please add your key to a `.env` file in the project root.")
        return None

    try:
        # Configure the client
        genai.configure(api_key=API_KEY)

        # Set up generation config
        generation_config = {
            "temperature": 0.3,
            "response_mime_type": "application/json",
        }
        
        system_prompt = get_conflict_resolution_prompt(conflict_data)

        # Initialize the model
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            generation_config=generation_config,
            system_instruction=system_prompt
        )

        # Send the prompt
        response = model.generate_content("Analyze this conflict and provide resolution.")
        
        # Parse response
        response_text = response.text.strip()
        return json.loads(response_text)

    except json.JSONDecodeError:
        console.print("[bold red]Error: Failed to decode AI response.[/bold red]")
        console.print(f"Raw response: {response_text}")
        return None
    except Exception as e:
        console.print(f"[bold red]An API error occurred: {e}[/bold red]")
        return None