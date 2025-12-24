import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

def list_models():
    api_key = os.getenv("GEMINI_API_KEY")
    client = genai.Client(api_key=api_key)
    
    print("Listing available models:")
    for model in client.models.list():
        # Using getattr to be safe if the attribute name varies
        name = getattr(model, 'name', 'Unknown')
        actions = getattr(model, 'supported_actions', 'Unknown')
        print(f"Name: {name}, Actions: {actions}")

if __name__ == "__main__":
    list_models()