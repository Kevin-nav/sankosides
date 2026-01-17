# Phase 2: Citation System & Auditor Agent

## Overview
Implement inline citations, Citation Auditor agent for verification, and proper citation formatting using the render service.

---

## 2.1 Reference Configuration Schema

### File: `sanko-backend/app/core/university_configs/base.py`

Add `ReferenceConfig` class:
```python
class ReferenceConfig(BaseModel):
    """
    Configuration for citation and reference behavior.
    Each university can have custom rules.
    """
    # Inline citation format
    inline_format: Literal["author_year", "numbered"] = Field(
        default="author_year",
        description="Format for inline citations: (Smith, 2024) or [1]"
    )
    
    # Multiple citations per statement
    allow_multiple_citations: bool = Field(
        default=True,
        description="Allow (Smith, 2024; Jones, 2023) format"
    )
    
    # Reference list ordering
    ordering: Literal["alphabetical", "appearance"] = Field(
        default="alphabetical",
        description="How to order references on References slide"
    )
    
    # Reference list numbering
    use_numbered_list: bool = Field(
        default=False,
        description="Use numbered list (for IEEE) vs bullets (for Harvard/APA)"
    )
    
    # Auto-detect from citation style
    @classmethod
    def from_citation_style(cls, style: str) -> "ReferenceConfig":
        """Create config based on citation style."""
        if style.lower() == "ieee":
            return cls(
                inline_format="numbered",
                ordering="appearance",
                use_numbered_list=True,
            )
        else:  # harvard, apa, chicago
            return cls(
                inline_format="author_year",
                ordering="alphabetical",
                use_numbered_list=False,
            )


class FormattingRules(BaseModel):
    # ...existing fields...
    references: ReferenceConfig = Field(default_factory=ReferenceConfig)
```

---

## 2.2 Citation Auditor Agent

### File: `sanko-backend/app/crew/agents/citation_auditor.py`

```python
"""
Citation Auditor Agent

Purpose: Verify all citations are valid and properly formatted.
Model: Gemini PRO for accuracy
Position: After Refiner, before Generator

Responsibilities:
1. Cross-reference inline citations with slide.citations
2. Validate DOIs via CrossRef API
3. Remove unverified inline citations
4. Fix formatting issues
5. Ensure zero-hallucination for citations
"""

from crewai import Agent, Task
from crewai.tools import BaseTool
from typing import Optional, List

from app.models.schemas import RefinedContent, RefinedSlide, CitationMetadata
from app.clients.gemini.llm import REFINER_LLM


AUDITOR_SYSTEM_PROMPT = """You are a meticulous citation auditor with zero tolerance for errors.

YOUR MISSION:
Verify every citation in the presentation is:
1. Real (exists in academic databases)
2. Properly formatted
3. Referenced correctly inline
4. Has valid metadata (DOI, authors, year)

## VERIFICATION PROCESS

### Step 1: Extract Inline Citations
From each bullet point, find all inline citations:
- Author-year format: (Smith, 2024), (Jones & Brown, 2023), (Lee et al., 2022)
- Numbered format: [1], [2], [3]

### Step 2: Cross-Reference
For each inline citation, verify it exists in the slide's `citations` array:
- (Smith, 2024) → must have CitationMetadata with authors containing "Smith" and year "2024"
- If no match found: REMOVE the inline citation from text OR add the citation if found via search

### Step 3: Validate DOIs
For each citation with a DOI:
- Use DOI validation tool to verify it's real
- If invalid: flag and attempt to find correct DOI

### Step 4: Format Verification
Verify citations match the required style:
- Harvard: (Surname, Year)
- APA: (Surname, Year)  
- IEEE: [Number]
- Chicago: (Surname Year)

### Step 5: Orphan Detection
Check for citations in the array that are never referenced inline:
- Keep them (they may be general sources)
- But flag if suspiciously many orphans

## OUTPUT
Return cleaned RefinedContent with:
- All inline citations verified
- Invalid citations removed
- Citation arrays updated
- Audit report with any issues found
"""


def create_citation_auditor_agent(
    llm=None,
    tools: Optional[List[BaseTool]] = None
) -> Agent:
    """Create the Citation Auditor Agent."""
    if llm is None:
        llm = REFINER_LLM()
    
    return Agent(
        role="Citation Auditor",
        goal="""Verify all citations are real, properly formatted, and correctly referenced.
        Remove any unverified citations. Ensure zero-hallucination for academic integrity.""",
        backstory="""You are a former academic journal editor with 15 years of experience
        catching citation errors. You've reviewed thousands of papers and can spot
        a fabricated citation instantly. Your reputation depends on absolute accuracy.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
        tools=tools or [],
    )


def create_auditing_task(
    agent: Agent,
    refined_content: RefinedContent,
    citation_style: str,
) -> Task:
    """Create task for citation auditing."""
    return Task(
        description=f"""Audit all citations in this presentation.

## PRESENTATION
Title: {refined_content.presentation_title}
Total Slides: {len(refined_content.slides)}
Citation Style: {citation_style.upper()}

## YOUR TASKS
1. Extract all inline citations from bullet points
2. Cross-reference each with slide.citations array
3. Remove any inline citations without matching metadata
4. Validate DOIs where present
5. Verify format matches {citation_style.upper()} style
6. Return cleaned content

CRITICAL: Do not fabricate any citations. If unverifiable, REMOVE.""",
        expected_output="""RefinedContent with all citations verified.
Any removed citations noted in audit report.""",
        agent=agent,
        output_pydantic=RefinedContent,
    )
```

---

## 2.3 DOI Validation Tool

### File: `sanko-backend/app/crew/tools/doi_validator.py`

```python
"""DOI Validation Tool for Citation Auditor."""

from crewai.tools import BaseTool
import httpx
from pydantic import BaseModel, Field
from typing import Optional


class DOIValidatorTool(BaseTool):
    name: str = "validate_doi"
    description: str = """Validate a DOI and retrieve its metadata.
    Input: DOI string (e.g., "10.1038/nature12373")
    Output: Validation result with metadata if valid."""
    
    async def _arun(self, doi: str) -> dict:
        """Validate DOI via CrossRef API."""
        # Clean DOI
        doi = doi.strip()
        if doi.startswith("https://doi.org/"):
            doi = doi.replace("https://doi.org/", "")
        
        url = f"https://api.crossref.org/works/{doi}"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    message = data.get("message", {})
                    return {
                        "valid": True,
                        "doi": doi,
                        "title": message.get("title", [""])[0],
                        "authors": [
                            f"{a.get('given', '')} {a.get('family', '')}"
                            for a in message.get("author", [])
                        ],
                        "year": message.get("published-print", {}).get("date-parts", [[None]])[0][0],
                        "journal": message.get("container-title", [""])[0],
                    }
                else:
                    return {"valid": False, "doi": doi, "error": f"HTTP {response.status_code}"}
            except Exception as e:
                return {"valid": False, "doi": doi, "error": str(e)}
    
    def _run(self, doi: str) -> dict:
        """Sync wrapper."""
        import asyncio
        return asyncio.get_event_loop().run_until_complete(self._arun(doi))
```

---

## 2.4 Inline Citation Extraction Utility

### File: `sanko-backend/app/services/citation_utils.py`

```python
"""Utilities for citation extraction and manipulation."""

import re
from typing import List, Tuple, Optional
from app.models.schemas import CitationMetadata


# Regex patterns for inline citations
AUTHOR_YEAR_PATTERN = r'\(([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?(?:\s+et\s+al\.)?),?\s*(\d{4}[a-z]?)\)'
# Matches: (Smith, 2024), (Jones and Brown, 2023), (Lee et al., 2022), (Amegbey, 1990a)

MULTIPLE_CITATION_PATTERN = r'\(([^)]+(?:;\s*[^)]+)+)\)'
# Matches: (Smith, 2024; Jones, 2023)

NUMBERED_PATTERN = r'\[(\d+)\]'
# Matches: [1], [2], [12]


def extract_inline_citations(text: str, format: str = "author_year") -> List[Tuple[str, str, int, int]]:
    """
    Extract inline citations from text.
    
    Returns list of (author, year, start_pos, end_pos) tuples.
    For numbered format, author is empty and year is the number.
    """
    results = []
    
    if format == "author_year":
        # First check for multiple citations
        for match in re.finditer(MULTIPLE_CITATION_PATTERN, text):
            full_match = match.group(0)
            inner = match.group(1)
            # Split by semicolon
            for part in inner.split(";"):
                part = part.strip()
                sub_match = re.match(r'([A-Z][a-z]+(?:\s+(?:and|&)\s+[A-Z][a-z]+)?(?:\s+et\s+al\.)?),?\s*(\d{4}[a-z]?)', part)
                if sub_match:
                    results.append((
                        sub_match.group(1),
                        sub_match.group(2),
                        match.start(),
                        match.end()
                    ))
        
        # Then single citations
        for match in re.finditer(AUTHOR_YEAR_PATTERN, text):
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
    """Find a citation that matches the inline reference."""
    year_clean = year.rstrip('abcdefghij')  # Remove year suffix like 2024a
    
    for citation in citations:
        # Check year matches
        if citation.year != year_clean and citation.year != year:
            continue
        
        # Check author matches
        author_lower = author.lower().replace(" et al.", "").replace(" and ", " ").strip()
        
        for cit_author in citation.authors:
            # Get surname (last part)
            surname = cit_author.split()[-1].lower()
            if surname in author_lower:
                return citation
    
    return None


def remove_inline_citation(text: str, start: int, end: int) -> str:
    """Remove an inline citation from text."""
    # Remove the citation and any extra space before it
    before = text[:start].rstrip()
    after = text[end:].lstrip()
    return before + " " + after if after else before
```

---

## 2.5 Integrate Auditor Into Pipeline

### File: `sanko-backend/app/crew/flows/slide_generation.py`

Add new method and integrate:
```python
from app.crew.agents.citation_auditor import create_citation_auditor_agent, create_auditing_task
from app.crew.tools.doi_validator import DOIValidatorTool
from app.services.citation_utils import extract_inline_citations, find_matching_citation, remove_inline_citation


async def _run_citation_auditor(self) -> RefinedContent:
    """
    Run Citation Auditor to verify all citations.
    Position: After Refiner, before Generator
    """
    await self.emitter.stage_start("citation_auditor")
    
    refined = self.state.refined_content
    citation_style = self.state.order_form.citation_style
    inline_format = "numbered" if citation_style == "ieee" else "author_year"
    
    # For each slide, verify inline citations
    for slide in refined.slides:
        for i, bullet in enumerate(slide.bullet_points):
            # Extract inline citations
            citations_found = extract_inline_citations(bullet, inline_format)
            
            for author, year, start, end in reversed(citations_found):
                # Check if citation exists in slide.citations
                match = find_matching_citation(author, year, slide.citations)
                
                if not match:
                    # Citation not found - remove from text
                    slide.bullet_points[i] = remove_inline_citation(bullet, start, end)
                    logger.warning(f"Removed unverified citation: ({author}, {year})")
    
    # Validate DOIs for all citations
    doi_tool = DOIValidatorTool()
    for slide in refined.slides:
        for citation in slide.citations:
            if citation.doi:
                result = await doi_tool._arun(citation.doi)
                if not result["valid"]:
                    logger.warning(f"Invalid DOI: {citation.doi}")
                    citation.verified = False
                else:
                    citation.verified = True
    
    await self.emitter.stage_complete("citation_auditor")
    return refined


# Update pipeline order:
async def run_full_pipeline(self):
    # ... existing steps ...
    await self._run_refiner()
    await self._run_citation_auditor()  # NEW: After Refiner
    await self._run_generator()
    # ... rest of pipeline ...
```

---

## 2.6 Render Service: HTML Citation Formatting

### File: `sanko-render-service/src/services/citation.service.js`

Update to support HTML output:
```javascript
function formatCitation(citation, style = 'apa', index = 0, outputFormat = 'text') {
    try {
        // ... existing CSL-JSON building ...
        
        const cite = new Cite([cslData]);
        
        // Choose output format
        const format = outputFormat === 'html' ? 'html' : 'text';
        
        const formatted = cite.format('bibliography', {
            format: format,
            template: style,
            lang: 'en-US'
        });

        return {
            index,
            original: citation,
            formatted: formatted.trim(),
            style,
            format: outputFormat,
        };

    } catch (err) {
        // ... existing fallback ...
    }
}

module.exports = { formatCitation };
```

### File: `sanko-render-service/src/routes/citation.routes.js`

Update endpoint:
```javascript
router.post('/render/citation', async (req, res) => {
    const { citations, style = 'apa', format = 'html' } = req.body;  // Default to HTML
    
    // ... rest of endpoint ...
    
    const formattedCitations = citations.map((citation, index) =>
        citationService.formatCitation(citation, style, index, format)
    );
    
    // ...
});
```

---

## 2.7 Format References Using Render Service

### File: `sanko-backend/app/crew/flows/slide_generation.py`

Update `_generate_references_slide`:
```python
async def _generate_references_slide(
    self,
    all_slides: List[RefinedSlide],
    citation_style: str,
    order: int,
) -> RefinedSlide:
    """Generate References slide with properly formatted citations."""
    import httpx
    from app.core.config import RENDER_SERVICE_URL
    
    # Collect unique citations
    seen_ids = set()
    all_citations = []
    for slide in all_slides:
        for citation in slide.citations:
            cid = citation.doi or f"{citation.title}_{citation.year}"
            if cid not in seen_ids:
                seen_ids.add(cid)
                all_citations.append(citation)
    
    # Sort based on style
    if citation_style in ["harvard", "apa", "chicago"]:
        all_citations.sort(key=lambda c: (c.authors[0] if c.authors else "ZZZ", c.year))
    
    # Call render service for formatting
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{RENDER_SERVICE_URL}/render/citation",
            json={
                "citations": [c.model_dump() for c in all_citations],
                "style": citation_style,
                "format": "html"
            },
            timeout=30.0
        )
        result = response.json()
    
    formatted = [c["formatted"] for c in result.get("citations", [])]
    
    return RefinedSlide(
        order=order,
        title="References",
        content_type=SlideContentType.REFERENCES,
        bullet_points=[],
        citations=all_citations,
        formatted_citations=formatted,
        template_type="references",
    )
```

---

## 2.8 Testing Checklist

- [ ] `ReferenceConfig` schema added
- [ ] Citation Auditor agent created
- [ ] DOI Validator tool works
- [ ] Inline citation extraction regex is accurate
- [ ] Unverified citations are removed from text
- [ ] Render service returns HTML-formatted citations
- [ ] References slide shows formatted citations with italics
- [ ] IEEE numbered format works
- [ ] Harvard/APA author-year format works
- [ ] Multiple citations per statement works

---

## Files Modified/Created

| File | Changes |
|------|---------|
| `app/core/university_configs/base.py` | Add `ReferenceConfig` |
| `app/crew/agents/citation_auditor.py` | NEW - Auditor agent |
| `app/crew/tools/doi_validator.py` | NEW - DOI validation |
| `app/services/citation_utils.py` | NEW - Citation extraction utils |
| `app/crew/flows/slide_generation.py` | Add auditor step, update references |
| `sanko-render-service/src/services/citation.service.js` | Add HTML format |
| `sanko-render-service/src/routes/citation.routes.js` | Add format param |
