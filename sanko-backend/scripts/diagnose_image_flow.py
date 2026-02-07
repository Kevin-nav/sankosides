"""
Diagnose Image Flow Script

End-to-end test of the image pipeline from PlannedSlide to RefinedSlide.
Simulates the actual slide generation flow to identify where images are lost.

Usage:
    cd c:/Users/Kevin/Projects/personal_projects/sankoslides/sanko-backend
    .\\venv\\Scripts\\Activate.ps1
    python scripts/diagnose_image_flow.py
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def diagnose_flow():
    """Run end-to-end diagnosis of image flow."""
    print("=" * 60)
    print("🔬 Image Flow Diagnostic Script")
    print("=" * 60)
    print()
    
    # Import required modules
    from app.models.schemas import SlideContentType
    from app.crew.flows.slide_generation import PlannedSlide
    from app.crew.agents.image_source_agent import ImageSourceAgent
    
    # Step 1: Create test PlannedSlide with image_query
    print("📋 Step 1: Creating Test PlannedSlide")
    print("-" * 40)
    
    test_slide = PlannedSlide(
        order=1,
        title="Introduction to Machine Learning",
        content_type=SlideContentType.CONTENT,
        bullet_points=[
            "Machine learning enables computers to learn from data",
            "Three main types: supervised, unsupervised, and reinforcement learning",
            "Applications include image recognition, NLP, and recommendation systems"
        ],
        image_query="Machine learning concept visualization with neural networks",
        template_type="content_with_image",
    )
    
    print(f"✅ Created PlannedSlide:")
    print(f"   Title: {test_slide.title}")
    print(f"   image_query: {test_slide.image_query}")
    print(f"   template_type: {test_slide.template_type}")
    print()
    
    # Step 2: Test ImageSourceAgent
    print("📋 Step 2: Running ImageSourceAgent.find_image()")
    print("-" * 40)
    
    try:
        image_agent = ImageSourceAgent()
        
        result = await image_agent.find_image(
            query=test_slide.image_query,
            slide_context=test_slide.title,
            style="academic",
        )
        
        print(f"✅ ImageSourceAgent returned:")
        print(f"   source_method: {result.source_method}")
        print(f"   verification_score: {result.verification_score:.2f}")
        print(f"   image_url: {result.image_url[:80]}..." if len(result.image_url) > 80 else f"   image_url: {result.image_url}")
        print(f"   image_alt: {result.image_alt}")
        print(f"   image_caption: {result.image_caption}")
        print()
        
        await image_agent.close()
        
    except Exception as e:
        print(f"❌ ImageSourceAgent failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Simulate RefinedSlide creation
    print("📋 Step 3: Simulating RefinedSlide Creation")
    print("-" * 40)
    
    from app.models.schemas import RefinedSlide
    
    refined = RefinedSlide(
        order=test_slide.order,
        title=test_slide.title,
        content_type=test_slide.content_type,
        bullet_points=test_slide.bullet_points,
        template_type=test_slide.template_type or "content",
        # These would be set by _refine_slide_enhanced
        image_url=result.image_url,
        image_alt=result.image_alt,
        image_caption=result.image_caption,
        image_citation=result.citation,
    )
    
    print(f"✅ Created RefinedSlide:")
    print(f"   image_url set: {bool(refined.image_url)}")
    print(f"   image_alt set: {bool(refined.image_alt)}")
    print(f"   image_citation set: {bool(refined.image_citation)}")
    print()
    
    # Step 4: Check URL accessibility
    print("📋 Step 4: Checking URL Accessibility")
    print("-" * 40)
    
    import httpx
    
    if refined.image_url and refined.image_url.startswith("http"):
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.head(refined.image_url, follow_redirects=True)
                
                if response.status_code == 200:
                    content_type = response.headers.get("content-type", "unknown")
                    print(f"✅ URL is accessible: HTTP 200, Content-Type: {content_type}")
                else:
                    print(f"❌ URL returned HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ URL check failed: {e}")
    elif refined.image_url:
        print(f"⚠️  URL is local path (R2 upload may have failed): {refined.image_url}")
    else:
        print("❌ No image URL set on RefinedSlide")
    
    print()
    
    # Step 5: Check if placeholder was returned
    print("📋 Step 5: Checking for Placeholder")
    print("-" * 40)
    
    if "placeholder" in refined.image_url.lower() or result.source_method == "placeholder":
        print("⚠️  PLACEHOLDER IMAGE DETECTED!")
        print("   This means image generation FAILED and a fallback was used.")
        print("   Check logs above for the specific failure reason.")
    else:
        print("✅ Real image generated (not a placeholder)")
    
    print()
    
    # Summary
    print("=" * 60)
    print("📊 Diagnosis Summary")
    print("=" * 60)
    
    issues = []
    
    if not test_slide.image_query:
        issues.append("❌ PlannedSlide has no image_query")
    
    if result.source_method == "placeholder":
        issues.append("❌ Image generation returned placeholder (generation failed)")
    
    if not refined.image_url:
        issues.append("❌ RefinedSlide has no image_url")
    elif not refined.image_url.startswith("http"):
        issues.append("⚠️  Image URL is local path, not R2 URL")
    
    if issues:
        print("\n".join(issues))
    else:
        print("✅ Image flow is working correctly!")
        print(f"   Final URL: {refined.image_url}")


if __name__ == "__main__":
    asyncio.run(diagnose_flow())
