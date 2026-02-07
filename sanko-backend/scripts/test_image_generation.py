"""
AI Image Generation Test Script

Standalone diagnostic to verify the image generation pipeline:
1. Gemini API connectivity
2. Image generation with sample prompt
3. R2 upload
4. Public URL accessibility

Usage:
    cd c:/Users/Kevin/Projects/personal_projects/sankoslides/sanko-backend
    .\\venv\\Scripts\\Activate.ps1
    python scripts/test_image_generation.py
"""

import asyncio
import sys
import os
import httpx

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_status(step: str, success: bool, message: str = ""):
    """Print formatted status."""
    icon = "✅" if success else "❌"
    print(f"{icon} {step}: {message}")


async def test_gemini_api_key():
    """Test that Gemini API key is configured."""
    try:
        from app.core.config import settings
        
        if not settings.gemini_api_key:
            print_status("Gemini API Key", False, "Not configured in settings")
            return False
        
        # Mask the key for display
        masked = settings.gemini_api_key[:8] + "..." + settings.gemini_api_key[-4:]
        print_status("Gemini API Key", True, f"Found: {masked}")
        return True
    except Exception as e:
        print_status("Gemini API Key", False, str(e))
        return False


async def test_r2_storage():
    """Test R2 storage connectivity."""
    try:
        from app.services.storage import get_storage_service
        
        storage = get_storage_service()
        
        # Check if bucket name is configured
        if not storage.bucket_name:
            print_status("R2 Storage", False, "Bucket name not configured")
            return False
        
        print_status("R2 Storage", True, f"Bucket: {storage.bucket_name}")
        return True
    except Exception as e:
        print_status("R2 Storage", False, str(e))
        return False


async def test_image_generation():
    """Test actual image generation with Gemini."""
    try:
        from app.crew.tools.image_generation_tool import NanoBananaImageTool
        
        print("\n🔄 Testing image generation (this may take 10-30 seconds)...")
        
        tool = NanoBananaImageTool()
        
        # Test with a simple prompt
        result = await tool.generate_asset(
            prompt="A simple blue circle on a white background",
            style="minimalist, clean",
            upload_to_r2=True,
        )
        
        if result.success:
            print_status("Image Generation", True, f"Generated successfully")
            print(f"   📍 File path/URL: {result.file_path}")
            print(f"   📝 Prompt used: {result.prompt_used[:50]}...")
            return result.file_path
        else:
            print_status("Image Generation", False, result.error or "Unknown error")
            return None
            
    except Exception as e:
        print_status("Image Generation", False, str(e))
        import traceback
        traceback.print_exc()
        return None


async def test_url_accessibility(url: str):
    """Test if the generated URL is accessible."""
    if not url:
        print_status("URL Accessibility", False, "No URL to test")
        return False
    
    if not url.startswith("http"):
        print_status("URL Accessibility", False, f"Not an HTTP URL: {url}")
        return False
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.head(url, follow_redirects=True)
            
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "unknown")
                print_status("URL Accessibility", True, f"HTTP 200, Content-Type: {content_type}")
                return True
            else:
                print_status("URL Accessibility", False, f"HTTP {response.status_code}")
                return False
                
    except Exception as e:
        print_status("URL Accessibility", False, str(e))
        return False


async def test_image_source_agent():
    """Test the full ImageSourceAgent flow."""
    try:
        from app.crew.agents.image_source_agent import ImageSourceAgent
        
        print("\n🔄 Testing ImageSourceAgent (full pipeline)...")
        
        agent = ImageSourceAgent()
        result = await agent.find_image(
            query="Neural network diagram",
            slide_context="Introduction to Deep Learning",
            style="academic",
        )
        
        print_status("ImageSourceAgent", True, f"Method: {result.source_method}")
        print(f"   📍 URL: {result.image_url[:80]}..." if len(result.image_url) > 80 else f"   📍 URL: {result.image_url}")
        print(f"   📊 Score: {result.verification_score:.2f}")
        print(f"   📝 Alt: {result.image_alt}")
        
        await agent.close()
        return result.image_url
        
    except Exception as e:
        print_status("ImageSourceAgent", False, str(e))
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run all diagnostic tests."""
    print("=" * 60)
    print("🔬 AI Image Generation Diagnostic Script")
    print("=" * 60)
    print()
    
    # Step 1: Check API key
    print("📋 Step 1: Checking Configuration")
    print("-" * 40)
    api_ok = await test_gemini_api_key()
    r2_ok = await test_r2_storage()
    
    if not api_ok:
        print("\n⛔ Cannot proceed without Gemini API key")
        return
    
    # Step 2: Test basic image generation
    print("\n📋 Step 2: Testing Image Generation")
    print("-" * 40)
    image_url = await test_image_generation()
    
    # Step 3: Test URL accessibility
    print("\n📋 Step 3: Testing URL Accessibility")
    print("-" * 40)
    if image_url:
        await test_url_accessibility(image_url)
    
    # Step 4: Test full agent flow
    print("\n📋 Step 4: Testing Full ImageSourceAgent Flow")
    print("-" * 40)
    agent_url = await test_image_source_agent()
    
    if agent_url:
        await test_url_accessibility(agent_url)
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    if image_url and image_url.startswith("http"):
        print("✅ Image generation pipeline is working!")
        print(f"   Generated URL: {image_url}")
    elif image_url:
        print("⚠️  Images generate but R2 upload may be failing (local path returned)")
        print(f"   Local path: {image_url}")
    else:
        print("❌ Image generation is failing. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
