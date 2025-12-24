import os
import json
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

PROMPT = """
You are a specialized STEM content extractor. Your goal is to convert the provided PDF into a high-fidelity Markdown representation suitable for academic slide generation.

FOLLOW THESE STRICT RULES:
1. STRUCTURE: Use clear Markdown headers (#, ##, ###) to represent the hierarchy of the document.
2. EQUATIONS: Extract ALL mathematical formulas and equations as valid LaTeX. Use $...$ for inline and $$...$$ for block equations.
3. VISUAL ELEMENTS: 
   - Identify every diagram, chart, circuit, or image.
   - For each visual element, provide a detailed [Visual Description: ...] tag describing what the image shows and its significance to the surrounding text.
   - If there is text inside a diagram, transcribe it accurately.
4. CITATIONS: Preserve all citations (e.g., [1], (Smith et al., 2023)).
5. TEXT: Maintain the technical and formal tone. Do not summarize; extract the core technical content.
6. ZERO HALLUCINATION: If you are unsure about a symbol or part of a diagram, indicate it with [?] or a descriptive note.

Output ONLY the Markdown content.
"""

def process_pdf(pdf_path: str, output_path: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found.")
        return

    client = genai.Client(api_key=api_key)
    
    print(f"Processing: {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        pdf_data = f.read()

    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            contents=[
                types.Part.from_bytes(data=pdf_data, mime_type="application/pdf"),
                PROMPT
            ],
            config=types.GenerateContentConfig(
                temperature=0.1, # Low temperature for high fidelity
            )
        )
        
        # Ensure results directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(response.text)
            
        print(f"Successfully saved to: {output_path}")
        return True
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return False

def run_poc():
    test_pdfs = [
        ("pdfs_for_testing/Calculus 166.pdf", "research/synthesis_poc/results/calculus_output.md"),
        ("pdfs_for_testing/ENGINEERING DRAWING R3.pdf", "research/synthesis_poc/results/drawing_output.md"),
        ("pdfs_for_testing/Complete Lecture Notes.pdf", "research/synthesis_poc/results/notes_output.md"),
    ]
    
    for pdf, out in test_pdfs:
        if os.path.exists(pdf):
            process_pdf(pdf, out)
        else:
            print(f"Skipping missing file: {pdf}")

if __name__ == "__main__":
    run_poc()
