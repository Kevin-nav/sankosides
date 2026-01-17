"""Utilities for citation extraction and manipulation.

Provides regex-based tools for:
- Extracting inline citations from text
- Matching inline citations to CitationMetadata
- Removing unverified citations from text
"""

import re
from typing import List, Tuple, Optional
from app.models.schemas import CitationMetadata


# =============================================================================
# Regex Patterns for Inline Citations
# =============================================================================

# Author-year format patterns
# Matches: (Smith, 2024), (Jones and Brown, 2023), (Lee et al., 2022), (Amegbey, 1990a)
AUTHOR_YEAR_PATTERN = r'\(([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?(?:\s+et\s+al\.)?),?\s*(\d{4}[a-z]?)\)'

# Multiple citations in one statement
# Matches: (Smith, 2024; Jones, 2023)
MULTIPLE_CITATION_PATTERN = r'\(([^)]+(?:;\s*[^)]+)+)\)'

# Numbered format for IEEE style
# Matches: [1], [2], [12]
NUMBERED_PATTERN = r'\[(\d+)\]'

# Multiple numbered citations
# Matches: [1, 2], [1-3], [1, 3, 5]
NUMBERED_RANGE_PATTERN = r'\[(\d+(?:\s*[-,]\s*\d+)*)\]'


# =============================================================================
# Citation Extraction Functions
# =============================================================================

def extract_inline_citations(
    text: str, 
    format: str = "author_year"
) -> List[Tuple[str, str, int, int]]:
    """
    Extract inline citations from text.
    
    Args:
        text: The text to search for citations
        format: Citation format ("author_year" or "numbered")
    
    Returns:
        List of (author, year, start_pos, end_pos) tuples.
        For numbered format, author is empty and year is the number.
    """
    results = []
    
    if format == "author_year":
        # First check for multiple citations (Smith, 2024; Jones, 2023)
        for match in re.finditer(MULTIPLE_CITATION_PATTERN, text):
            full_match = match.group(0)
            inner = match.group(1)
            
            # Split by semicolon
            for part in inner.split(";"):
                part = part.strip()
                sub_match = re.match(
                    r'([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?(?:\s+et\s+al\.)?),?\s*(\d{4}[a-z]?)', 
                    part
                )
                if sub_match:
                    results.append((
                        sub_match.group(1),
                        sub_match.group(2),
                        match.start(),
                        match.end()
                    ))
        
        # Then single citations not part of multiple
        for match in re.finditer(AUTHOR_YEAR_PATTERN, text):
            # Check if this is already part of a multiple citation
            is_part_of_multiple = False
            for existing in results:
                if existing[2] <= match.start() and match.end() <= existing[3]:
                    is_part_of_multiple = True
                    break
            
            if not is_part_of_multiple:
                results.append((
                    match.group(1),
                    match.group(2),
                    match.start(),
                    match.end()
                ))
    
    elif format == "numbered":
        for match in re.finditer(NUMBERED_PATTERN, text):
            results.append((
                "",
                match.group(1),
                match.start(),
                match.end()
            ))
    
    return results


def find_matching_citation(
    author: str,
    year: str,
    citations: List[CitationMetadata]
) -> Optional[CitationMetadata]:
    """
    Find a citation that matches the inline reference.
    
    Args:
        author: Author name(s) from inline citation
        year: Year from inline citation
        citations: List of CitationMetadata to search
    
    Returns:
        Matching CitationMetadata or None if not found
    """
    year_clean = year.rstrip('abcdefghij')  # Remove year suffix like 2024a
    
    for citation in citations:
        # Check year matches
        citation_year = str(citation.year).rstrip('abcdefghij') if citation.year else ""
        if citation_year != year_clean and citation_year != year:
            continue
        
        # Check author matches
        author_lower = author.lower().replace(" et al.", "").replace(" and ", " ").replace(" & ", " ").strip()
        
        for cit_author in citation.authors:
            # Get surname (last part of name)
            surname = cit_author.split()[-1].lower() if cit_author else ""
            if surname and surname in author_lower:
                return citation
    
    return None


def find_citation_by_number(
    number: int,
    citations: List[CitationMetadata],
    citation_order: List[CitationMetadata]
) -> Optional[CitationMetadata]:
    """
    Find a citation by its number in IEEE style.
    
    Args:
        number: The citation number (1-indexed)
        citations: List of CitationMetadata on the slide
        citation_order: Ordered list of all citations in appearance order
    
    Returns:
        Matching CitationMetadata or None if not found
    """
    if 1 <= number <= len(citation_order):
        target = citation_order[number - 1]
        # Verify it's in the slide's citations
        for cit in citations:
            if cit.doi == target.doi or (cit.title == target.title and cit.year == target.year):
                return cit
    return None


def remove_inline_citation(text: str, start: int, end: int) -> str:
    """
    Remove an inline citation from text.
    
    Args:
        text: The original text
        start: Start position of citation
        end: End position of citation
    
    Returns:
        Text with citation removed and spacing cleaned up
    """
    # Remove the citation and clean up spacing
    before = text[:start].rstrip()
    after = text[end:].lstrip()
    
    # Add single space between parts if needed
    if before and after and not before.endswith(('.', ',', ':', ';', '?', '!')):
        return before + " " + after
    elif before and after:
        return before + after
    elif before:
        return before
    else:
        return after


def extract_all_citations_from_slides(slides: List) -> List[CitationMetadata]:
    """
    Extract all unique citations from a list of slides.
    
    Args:
        slides: List of RefinedSlide objects
    
    Returns:
        List of unique CitationMetadata objects
    """
    seen_ids = set()
    all_citations = []
    
    for slide in slides:
        for citation in getattr(slide, 'citations', []):
            # Create unique ID from DOI or title+year
            cid = citation.doi if citation.doi else f"{citation.title}_{citation.year}"
            if cid not in seen_ids:
                seen_ids.add(cid)
                all_citations.append(citation)
    
    return all_citations


def sort_citations(
    citations: List[CitationMetadata],
    ordering: str = "alphabetical"
) -> List[CitationMetadata]:
    """
    Sort citations based on the specified ordering.
    
    Args:
        citations: List of CitationMetadata to sort
        ordering: "alphabetical" (by first author surname) or "appearance" (unchanged)
    
    Returns:
        Sorted list of CitationMetadata
    """
    if ordering == "alphabetical":
        def get_sort_key(cit):
            if cit.authors:
                # Get first author's surname (last part of name)
                first_author = cit.authors[0]
                surname = first_author.split()[-1].lower() if first_author else "zzz"
            else:
                surname = "zzz"
            return (surname, cit.year or "9999")
        
        return sorted(citations, key=get_sort_key)
    else:
        # Appearance order - keep as is
        return list(citations)
