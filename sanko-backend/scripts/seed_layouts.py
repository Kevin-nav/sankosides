import asyncio
import sys
import os

# Add parent directory to path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
import app.core.database as db
from app.core.template_models import SlideTemplate, ThemeConfig

# =============================================================================
# Modern Layouts (Clean, minimal, left-aligned, asymmetry)
# =============================================================================

MODERN_TITLE = """
<div class="slide slide-title-modern">
    <div class="accent-bar"></div>
    <div class="content">
        <h1>{{ slide.title }}</h1>
        <div class="subtitle">{{ slide.subtitle }}</div>
        
        <div class="footer-info">
            <span class="author">{{ slide.author }}</span>
            <span class="separator">|</span>
            <span class="date">{{ slide.date }}</span>
        </div>
    </div>
</div>

<style>
.slide-title-modern {
    display: flex;
    flex-direction: row;
    padding: 0;
    position: relative;
    background: var(--color-background);
}

.slide-title-modern .accent-bar {
    width: 60px;
    height: 100%;
    background: var(--color-primary);
    margin-right: var(--spacing-lg);
}

.slide-title-modern .content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: var(--spacing-lg);
}

.slide-title-modern h1 {
    font-size: calc(var(--font-size-title) * 1.2);
    font-weight: 800;
    color: var(--color-text-primary);
    margin-bottom: var(--spacing-md);
    letter-spacing: -0.02em;
    line-height: 1.1;
}

.slide-title-modern .subtitle {
    font-size: var(--font-size-heading);
    color: var(--color-secondary);
    font-weight: 500;
    margin-bottom: calc(var(--spacing-lg) * 2);
}

.slide-title-modern .footer-info {
    font-size: var(--font-size-body);
    color: var(--color-text-secondary);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
}

.slide-title-modern .separator {
    color: var(--color-accent);
}
</style>
"""

MODERN_CONTENT = """
<div class="slide slide-content-modern">
    <div class="header">
        <div class="accent-dot"></div>
        <h2>{{ slide.title }}</h2>
    </div>
    
    <div class="content-area">
        <ul>
            {% for point in slide.bullet_points %}
            <li class="card-item">{{ point }}</li>
            {% endfor %}
        </ul>
    </div>
</div>

<style>
.slide-content-modern {
    padding: var(--spacing-lg) calc(var(--spacing-lg) * 2);
}

.slide-content-modern .header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: calc(var(--spacing-lg) * 1.5);
    border-bottom: 2px solid var(--color-surface);
    padding-bottom: var(--spacing-sm);
}

.slide-content-modern .accent-dot {
    width: 12px;
    height: 12px;
    background: var(--color-accent);
    border-radius: 2px;
}

.slide-content-modern h2 {
    font-size: var(--font-size-heading);
    color: var(--color-primary);
    font-weight: 700;
    margin: 0;
}

.slide-content-modern ul {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--spacing-md);
    list-style: none;
    padding: 0;
}

.slide-content-modern li.card-item {
    background: var(--color-surface);
    padding: var(--spacing-md) var(--spacing-lg);
    border-radius: var(--radius-md);
    border-left: 4px solid var(--color-secondary);
    font-size: var(--font-size-body);
    color: var(--color-text-primary);
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
}
</style>
"""

# =============================================================================
# Split Layouts (50/50 division, bold blocks)
# =============================================================================

SPLIT_TITLE = """
<div class="slide slide-title-split">
    <div class="left-pane">
        <h1>{{ slide.title }}</h1>
    </div>
    <div class="right-pane">
        <div class="meta-content">
            <div class="subtitle">{{ slide.subtitle }}</div>
            <div class="divider"></div>
            <div class="author-block">
                <strong>{{ slide.author }}</strong><br>
                {{ slide.date }}
            </div>
        </div>
    </div>
</div>

<style>
.slide-title-split {
    display: flex;
    padding: 0;
    width: 100%;
    height: 100%;
}

.slide-title-split .left-pane {
    flex: 1;
    background: var(--color-primary);
    color: white; /* Force white text on primary block */
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-lg);
    text-align: right;
}

.slide-title-split .left-pane h1 {
    font-size: calc(var(--font-size-title) * 1.1);
    font-weight: 900;
    line-height: 1.1;
    color: white !important; /* Override theme text color */
}

.slide-title-split .right-pane {
    flex: 1;
    background: var(--color-surface);
    display: flex;
    align-items: center;
    padding: var(--spacing-lg);
}

.slide-title-split .meta-content {
    border-left: 1px solid var(--color-border);
    padding-left: var(--spacing-lg);
}

.slide-title-split .subtitle {
    font-size: var(--font-size-heading);
    color: var(--color-secondary);
    font-weight: 600;
    margin-bottom: var(--spacing-lg);
}

.slide-title-split .divider {
    width: 40px;
    height: 4px;
    background: var(--color-accent);
    margin-bottom: var(--spacing-lg);
}

.slide-title-split .author-block {
    font-size: var(--font-size-body);
    color: var(--color-text-secondary);
    line-height: 1.6;
}
</style>
"""

SPLIT_CONTENT = """
<div class="slide slide-content-split">
    <div class="sidebar">
        <h2>{{ slide.title }}</h2>
        <div class="decoration"></div>
    </div>
    <div class="main-content">
        <ul>
            {% for point in slide.bullet_points %}
            <li>{{ point }}</li>
            {% endfor %}
        </ul>
    </div>
</div>

<style>
.slide-content-split {
    display: flex;
    padding: 0;
}

.slide-content-split .sidebar {
    width: 30%;
    background: var(--color-surface);
    padding: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    justify-content: center;
    border-right: 1px solid var(--color-border);
}

.slide-content-split .sidebar h2 {
    font-size: var(--font-size-heading);
    color: var(--color-primary);
    font-weight: 800;
    margin-bottom: var(--spacing-md);
    text-align: right;
}

.slide-content-split .decoration {
    align-self: flex-end;
    width: 60px;
    height: 8px;
    background: var(--color-secondary);
    border-radius: 4px;
}

.slide-content-split .main-content {
    flex: 1;
    padding: calc(var(--spacing-lg) * 2);
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.slide-content-split ul {
    list-style: none;
    padding: 0;
}

.slide-content-split li {
    font-size: var(--font-size-body);
    margin-bottom: var(--spacing-md);
    padding-left: var(--spacing-lg);
    border-left: 2px solid var(--color-border);
    transition: all 0.3s ease;
}

.slide-content-split li:hover {
    border-left-color: var(--color-accent);
    padding-left: calc(var(--spacing-lg) + 5px);
}
</style>
"""

async def seed_layouts():
    print("Initializing DB...")
    db.init_async_db()
    
    async with db.AsyncSessionLocal() as session:
        print("Inserting templates...")
        
        new_templates = [
            SlideTemplate(
                template_id="title_modern",
                name="Modern Title",
                content_type="title",
                category="modern",
                html_template=MODERN_TITLE,
                css_styles="",
                version="1.0"
            ),
            SlideTemplate(
                template_id="content_modern",
                name="Modern Content",
                content_type="content",
                category="modern",
                html_template=MODERN_CONTENT,
                css_styles="",
                version="1.0"
            ),
            SlideTemplate(
                template_id="title_split",
                name="Split Title",
                content_type="title",
                category="split",
                html_template=SPLIT_TITLE,
                css_styles="",
                version="1.0"
            ),
            SlideTemplate(
                template_id="content_split",
                name="Split Content",
                content_type="content",
                category="split",
                html_template=SPLIT_CONTENT,
                css_styles="",
                version="1.0"
            ),
            # Add section layouts reusing modern styles just for demo
             SlideTemplate(
                template_id="section_modern",
                name="Modern Section",
                content_type="section",
                category="modern",
                html_template=MODERN_TITLE.replace("slide-title-modern", "slide-section-modern").replace("subtitle", "section-subtitle"), # Quick hack reusing title layout
                css_styles="",
                version="1.0"
            ),
             SlideTemplate(
                template_id="section_split",
                name="Split Section",
                content_type="section",
                category="split",
                html_template=SPLIT_TITLE, # Reuse split title
                css_styles="",
                version="1.0"
            ),
        ]
        
        for t in new_templates:
            # Upsert
            existing = await session.execute(select(SlideTemplate).where(SlideTemplate.template_id == t.template_id))
            existing = existing.scalar_one_or_none()
            
            if existing:
                print(f"Updating {t.template_id}")
                existing.html_template = t.html_template
                # Update other fields if needed
            else:
                print(f"Creating {t.template_id}")
                session.add(t)
        
        print("Updating Themes...")
        # Get all themes
        result = await session.execute(select(ThemeConfig))
        themes = result.scalars().all()
        
        # Heuristic assignment
        for theme in themes:
            if "ocean" in theme.name.lower() or "azure" in theme.name.lower() or "modern" in theme.name.lower():
                theme.layout_style = "modern"
                print(f"Set {theme.name} to Modern layout")
            elif "dark" in theme.name.lower() or "night" in theme.name.lower() or "bold" in theme.name.lower():
                theme.layout_style = "split"
                print(f"Set {theme.name} to Split layout")
            else:
                theme.layout_style = "default"
                print(f"Set {theme.name} to Default layout")
                
        await session.commit()
        print("Done!")

if __name__ == "__main__":
    asyncio.run(seed_layouts())
