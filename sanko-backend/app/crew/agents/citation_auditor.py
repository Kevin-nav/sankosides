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
    """
    Create the Citation Auditor Agent.
    
    This agent verifies all citations are real and properly formatted,
    ensuring zero-hallucination for academic integrity.
    
    Args:
        llm: The LLM instance (defaults to REFINER_LLM/PRO if not provided)
        tools: Optional tools (DOIValidatorTool)
        
    Returns:
        Configured CrewAI Agent
    """
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
    """
    Create task for citation auditing.
    
    Args:
        agent: The Citation Auditor agent
        refined_content: Content from Refiner to audit
        citation_style: The citation style being used (apa, ieee, harvard, chicago)
        
    Returns:
        CrewAI Task for citation auditing
    """
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


# Agent configuration as YAML-compatible dict
AUDITOR_CONFIG = {
    "role": "Citation Auditor",
    "goal": "Verify all citations are real and remove any that cannot be verified.",
    "backstory": "Meticulous journal editor with 15+ years catching citation errors.",
    "llm": "gemini/gemini-3-pro-preview",
    "thinking_level": "high",
    "memory": True,
    "verbose": True,
    "tools": ["DOIValidatorTool"],
}
