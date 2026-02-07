
import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent))

from app.templates.html_generator import generate_slide_html_with_db_template
from app.routers.generation.models import EnrichedSlide
from app.themes import SlideTheme, ColorPalette, UniversityBranding
from app.models.schemas import SlideContentType

async def verify_rendering():
    print("🧪 Starting Rendering Verification...")
    
    # Create debug directory
    out_dir = Path(__file__).parent.parent / "debug_output"
    out_dir.mkdir(exist_ok=True)
    
    # 1. Setup Theme
    theme = SlideTheme(
        id="modern-dark",
        name="Modern Dark",
        font_heading="Inter",
        font_body="Roboto",
        font_size_title="64px",
    )
    colors = ColorPalette(
        primary="#3B82F6",
        secondary="#10B981",
        background="#1F2937",
        text_primary="#F9FAFB",
        text_secondary="#9CA3AF",
        accent="#F59E0B"
    )
    branding = UniversityBranding(
        university_name="Verification University",
        university_badge_url="https://via.placeholder.com/150"
    )
    
    # 2. Define Test Slides
    slides_to_test = [
        EnrichedSlide(
            order=1,
            title="Introduction to Fluid Dynamics",
            content_type=SlideContentType.TITLE,
            subtitle="A Comprehensive Overview",
            presenter_name="Dr. Jane Doe"
        ),
        EnrichedSlide(
            order=2,
            title="Key Concepts",
            content_type=SlideContentType.CONTENT,
            bullet_points=[
                "Viscosity is a measure of a fluid's resistance to flow.",
                "Bernoulli's principle relates pressure, speed, and height.",
                "Reynolds number predicts flow patterns (laminar vs turbulent).",
                "Navier-Stokes equations describe the motion of viscous fluid substances."
            ]
        ),
        EnrichedSlide(
            order=3,
            title="The Equations",
            content_type=SlideContentType.CONTENT, # Will fallback to content but uses math
            bullet_points=["The core equation is:"],
            equation_latex=r"\\frac{\\partial \\rho}{\\partial t} + \\nabla \\cdot (\\rho \\mathbf{u}) = 0"
        ),
        EnrichedSlide(
            order=4,
            title="Process Timeline",
            content_type=SlideContentType.TIMELINE,
            bullet_points=[
                "Hypothesis Generation",
                "Experimental Design",
                "Data Collection",
                "Analysis & Conclusion"
            ]
        ),
        EnrichedSlide(
            order=5,
            title="By The Numbers",
            content_type=SlideContentType.BIG_STAT,
            big_stat_number="98%",
            big_stat_label="Accuracy Rate",
            bullet_points=["Accuracy Rate", "Achieved in double-blind trials"]
        ),
        EnrichedSlide(
            order=6,
            title="Split Layout",
            content_type=SlideContentType.TWO_COLUMN,
            left_column={"title": "Left Side", "content": ["Point A", "Point B"]},
            right_column={"title": "Right Side", "content": ["Point C", "Point D"]}
        )
    ]
    
    # 3. Generate HTML
    for slide in slides_to_test:
        print(f"Generating Slide {slide.order}: {slide.title} ({slide.content_type})...")
        html = await generate_slide_html_with_db_template(
            slide=slide,
            theme=theme,
            colors=colors,
            branding=branding,
            slide_number=slide.order,
            total_slides=len(slides_to_test)
        )
        
        filename = f"slide_{slide.order}_{slide.content_type}.html"
        (out_dir / filename).write_text(html, encoding="utf-8")
        print(f"  -> Saved to {out_dir / filename}")
        
    print(f"\n✨ Verification Complete! Check {out_dir} for results.")

if __name__ == "__main__":
    asyncio.run(verify_rendering())
