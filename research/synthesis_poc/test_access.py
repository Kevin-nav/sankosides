import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def test_gemini_3_flash():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in environment.")
        return

    client = genai.Client(api_key=api_key)
    
    # 1. Text Test
    print("Testing Text Prompt...")
    response = client.models.generate_content(
        model="gemini-3-flash-preview",
        contents="Hello Gemini 3 Flash! Respond with 'Ready' if you can hear me."
    )
    print(f"Text Response: {response.text}")

    # 2. Multimodal Test (using a small PDF if possible, or just checking if we can start an upload)
    print("\nTesting Multimodal (PDF) Input...")
    pdf_path = "pdfs_for_testing/Calculus 166.pdf"
    
    # Path is relative to the project root where I run the script
    if not os.path.exists(pdf_path):
        # Try relative to the script's location if running from research/synthesis_poc
        pdf_path = "../../pdfs_for_testing/Calculus 166.pdf"

    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_data = f.read()
        
        # Simple test: Ask about the title of the PDF
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_bytes(data=pdf_data, mime_type="application/pdf"),
                "What is the title of this document?"
            ]
        )
        print(f"Multimodal Response: {response.text}")
    else:
        print(f"Error: PDF not found at {pdf_path}")

if __name__ == "__main__":
    test_gemini_3_flash()
