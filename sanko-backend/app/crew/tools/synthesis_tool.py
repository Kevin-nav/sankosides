"""
Synthesis Tool for CrewAI

Purpose: Convert PDF documents into a structured KnowledgeBase
using Gemini 3 Flash multimodal capabilities.
"""

import os
import json
from pydantic import BaseModel, Field
from crewai.tools import BaseTool
from google import genai
from google.genai import types

from app.models.schemas import KnowledgeBase
from app.core.config import settings

# System prompt for the Gemini model
SYNTHESIS_PROMPT = """
You are a specialized STEM content extractor. Your goal is to convert the provided PDF into a structured JSON object representing a KnowledgeBase.

FOLLOW THESE STRICT RULES:
1.  **JSON Output:** Your entire output MUST be a single, valid JSON object.
2.  **Schema:** The JSON object must conform to this Pydantic schema:
    ```json
    {
      "summary": "High-level overview of the entire document set.",
      "sections": [
        {
          "title": "Section header or topic",
          "content": "Full text and latex content for this section.",
          "visuals": ["Description of any diagrams, charts, etc."],
          "page_range": "e.g., '1-3'"
        }
      ]
    }
    ```
3.  **Equations:** Extract ALL mathematical formulas as valid LaTeX within the 'content' field. Use $...$ for inline and $$...$$ for block equations.
4.  **Visuals:** Identify every diagram, chart, or image and add a detailed description to the 'visuals' list for that section.
5.  **Hierarchy:** Use the document's structure to create logical sections.

Output ONLY the JSON object. Do not include any other text or formatting.
"""

class SynthesisToolInput(BaseModel):
    """Input for the SynthesisTool."""
    file_path: str = Field(description="The path to the PDF file to be synthesized.")

class SynthesisTool(BaseTool):
    name: str = "PDF Synthesizer"
    description: str = "Processes a PDF file, extracting its structure, text, and visual elements into a structured KnowledgeBase."
    args_schema: type[BaseModel] = SynthesisToolInput

    def _run(self, file_path: str) -> KnowledgeBase:
        api_key = settings.gemini_api_key
        if not api_key:
            return "Error: GEMINI_API_KEY not configured."

        client = genai.Client(api_key=api_key)
        
        try:
            with open(file_path, "rb") as f:
                pdf_data = f.read()

            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=[
                    types.Part.from_bytes(data=pdf_data, mime_type="application/pdf"),
                    SYNTHESIS_PROMPT
                ],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                )
            )
            
            # The response should be a JSON string, parse it
            response_json = json.loads(response.text)
            knowledge_base = KnowledgeBase(**response_json)
            
            return knowledge_base

        except FileNotFoundError:
            return f"Error: File not found at {file_path}"
        except json.JSONDecodeError:
            return "Error: Failed to decode JSON from Gemini response."
        except Exception as e:
            return f"An unexpected error occurred: {e}"
