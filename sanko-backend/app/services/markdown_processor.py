"""
Markdown Processor for Slide Content

Converts Markdown formatting in AI-generated bullet points to HTML.
Supports: **bold**, *italic*, `code`, [links](url)

This runs as a post-processing step after the Refiner produces slides,
ensuring that any Markdown formatting from the AI is properly rendered.
"""

import re
from typing import List
from app.models.schemas import RefinedSlide
from app.core.logging import get_logger

logger = get_logger(__name__)


def process_markdown_in_slide(slide: RefinedSlide) -> RefinedSlide:
    """
    Convert Markdown formatting in bullet points to HTML.
    
    Supports:
    - **bold** → <strong>bold</strong>
    - *italic* → <em>italic</em>
    - `code` → <code>code</code>
    - [text](url) → <a href="url">text</a>
    
    Args:
        slide: RefinedSlide with potentially markdown-formatted content
        
    Returns:
        RefinedSlide with HTML-formatted content
    """
    if slide.bullet_points:
        slide.bullet_points = [
            _markdown_to_html(point) for point in slide.bullet_points
        ]
    
    # Also process title if it contains markdown
    if slide.title:
        slide.title = _markdown_to_html(slide.title)
    
    return slide


def process_all_slides(slides: List[RefinedSlide]) -> List[RefinedSlide]:
    """
    Process markdown in all slides.
    
    Args:
        slides: List of RefinedSlide objects
        
    Returns:
        List of slides with processed markdown
    """
    processed_count = 0
    for slide in slides:
        original_points = slide.bullet_points.copy() if slide.bullet_points else []
        process_markdown_in_slide(slide)
        if slide.bullet_points != original_points:
            processed_count += 1
    
    if processed_count > 0:
        logger.info(f"[MARKDOWN] Processed {processed_count} slides with markdown content")
    
    return slides


def _markdown_to_html(text: str) -> str:
    """
    Convert basic Markdown syntax to HTML.
    
    Order matters: we process bold before italic to handle nested cases.
    
    Args:
        text: Text potentially containing Markdown
        
    Returns:
        Text with Markdown converted to HTML
    """
    if not text:
        return text
    
    # Bold: **text** or __text__ → <strong>text</strong>
    # Use non-greedy match to handle multiple bold sections
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'__(.+?)__', r'<strong>\1</strong>', text)
    
    # Italic: *text* or _text_ → <em>text</em>
    # Be careful not to match underscores in the middle of words
    text = re.sub(r'(?<!\w)\*([^*]+)\*(?!\w)', r'<em>\1</em>', text)
    text = re.sub(r'(?<!\w)_([^_]+)_(?!\w)', r'<em>\1</em>', text)
    
    # Inline code: `code` → <code>code</code>
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)
    
    # Links: [text](url) → <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    # Superscript for citations: ^[n] → <sup>[n]</sup> (common in academic text)
    text = re.sub(r'\^\[(\d+)\]', r'<sup>[\1]</sup>', text)
    
    return text


def strip_markdown(text: str) -> str:
    """
    Remove Markdown formatting, returning plain text.
    Useful for generating speaker notes or plain-text exports.
    
    Args:
        text: Text containing Markdown
        
    Returns:
        Plain text without Markdown syntax
    """
    if not text:
        return text
    
    # Remove bold markers
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    
    # Remove italic markers
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    
    # Remove code markers
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # Convert links to just the text
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    
    # Remove superscript markers
    text = re.sub(r'\^\[(\d+)\]', r'[\1]', text)
    
    return text
