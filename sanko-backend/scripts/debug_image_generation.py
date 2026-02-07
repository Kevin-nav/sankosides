"""
Debug Image Generation - Check raw image data size before upload.
"""

import asyncio
import sys
import os
import base64

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google import genai
from google.genai import types
from app.core.config import settings


async def debug_image_generation():
    print("=" * 60)
    print("DEBUG: Image Generation Raw Data Check")
    print("=" * 60)
    
    # Initialize client
    client = genai.Client(api_key=settings.gemini_api_key)
    
    prompt = "A simple blue circle on a white background"
    full_prompt = f"{prompt}\n\nStyle: minimalist, clean"
    
    print(f"\nPrompt: {prompt}")
    print(f"Model: {settings.model_image}")
    print("\nGenerating image...")
    
    try:
        response = client.models.generate_content(
            model=settings.model_image,
            contents=[
                types.Content(
                    role="user",
                    parts=[types.Part(text=full_prompt)]
                )
            ],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )
        )
        
        print(f"\nResponse received!")
        print(f"Number of candidates: {len(response.candidates)}")
        
        for i, candidate in enumerate(response.candidates):
            print(f"\nCandidate {i}:")
            print(f"  Parts count: {len(candidate.content.parts)}")
            
            for j, part in enumerate(candidate.content.parts):
                print(f"\n  Part {j}:")
                
                if part.inline_data:
                    raw_data = part.inline_data.data
                    print(f"    Has inline_data: True")
                    print(f"    MIME type: {part.inline_data.mime_type}")
                    print(f"    Raw data type: {type(raw_data)}")
                    print(f"    Raw data length: {len(raw_data)}")
                    
                    # Check if it's already bytes or base64 string
                    if isinstance(raw_data, bytes):
                        image_data = raw_data
                        print(f"    Data format: Raw bytes")
                    else:
                        # It's a base64 string
                        print(f"    Data format: Base64 string")
                        print(f"    First 100 chars: {str(raw_data)[:100]}...")
                        image_data = base64.b64decode(raw_data)
                    
                    print(f"    Decoded size: {len(image_data)} bytes")
                    
                    # Check PNG signature
                    png_sig = image_data[:8]
                    expected_sig = b'\x89PNG\r\n\x1a\n'
                    is_valid_png = png_sig == expected_sig
                    print(f"    PNG signature valid: {is_valid_png}")
                    print(f"    First 20 bytes: {image_data[:20]}")
                    
                    # Save locally for inspection
                    with open("debug_generated_image.png", "wb") as f:
                        f.write(image_data)
                    print(f"\n    Saved to: debug_generated_image.png")
                    
                    # Try to open with PIL
                    try:
                        from PIL import Image
                        from io import BytesIO
                        img = Image.open(BytesIO(image_data))
                        print(f"    PIL opened: YES")
                        print(f"    Image size: {img.size}")
                        print(f"    Image format: {img.format}")
                    except Exception as e:
                        print(f"    PIL error: {e}")
                        
                elif part.text:
                    print(f"    Has text: {part.text[:200]}...")
                else:
                    print(f"    Unknown part type")
                    
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_image_generation())
