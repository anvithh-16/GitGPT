import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load API key from .env file
load_dotenv()
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    print("Error: GEMINI_API_KEY not found in .env file.")
    exit()

genai.configure(api_key=API_KEY)

print("--- Available Models ---")
for m in genai.list_models():
  # We only care about models that can be used for text generation
  if 'generateContent' in m.supported_generation_methods:
    print(f"* {m.name}")

print("-------------------------")
print("\nFind one of the models above (e.g., 'models/gemini-2.5-flash')")
print("and copy the name (without 'models/') into your api_client.py file.")