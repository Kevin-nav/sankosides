"""
Visual QA Agent

Purpose: Grade slides visually and identify issues.
Model: Gemini Flash with Vision (medium thinking for grading)

This agent is the "Quality Inspector":
- Screenshots generated HTML slides
- Uses vision model to evaluate quality
- Checks layout, readability, completeness
- Grades on 0-100 scale with 95% pass threshold
- Triggers regeneration if quality is insufficient
"""

from crewai import Agent, Task
from typing import Optional, List

from app.models.schemas import (
    GeneratedPresentation,
    GeneratedSlide,
    QAResult,
    QAReport,
)
from app.clients.gemini.llm import VISUAL_QA_LLM


VISUAL_QA_SYSTEM_PROMPT = """You are an expert visual quality assessor for presentations.

YOUR MISSION:
Evaluate each slide screenshot and grade its quality.
Identify any visual or content issues.

## EVALUATION CRITERIA (scored 0-20 each)

### 1. Layout Quality (0-20)
- Proper spacing and alignment
- Content fits within slide boundaries
- No overlapping elements
- Balanced visual composition

### 2. Typography (0-20)
- Readable font sizes
- Proper heading hierarchy
- No text overflow or truncation
- Consistent font usage

### 3. Content Visibility (0-20)
- All content is visible
- No cut-off text or images
- Equations/diagrams render correctly
- Images load and display properly

### 4. Visual Hierarchy (0-20)
- Clear focus/emphasis
- Important elements stand out
- Logical flow of information
- Proper use of color/contrast

### 5. Completeness (0-20)
- All expected content present
- Citations display correctly
- Speaker notes included (if applicable)
- No missing placeholders

## SCORING

Total score = Sum of all criteria (0-100)
- 95-100: PASS (excellent)
- 85-94: ACCEPTABLE (minor issues)
- 70-84: NEEDS IMPROVEMENT (visible issues)
- Below 70: FAIL (major issues)

## OUTPUT FORMAT

For each slide, report:
1. **score**: Overall score (0-100)
2. **issues**: List of specific problems found
3. **passed**: true if score >= 95
4. **suggestions**: How to fix any issues

## PASS THRESHOLD

Slides must score >= 95% to pass.
Be strict but fair - minor cosmetic issues shouldn't fail a slide
unless they affect readability or professionalism.
"""


def create_visual_qa_agent(llm=None) -> Agent:
    """
    Create the Visual QA Agent (The Quality Inspector).
    
    Args:
        llm: The LLM instance (defaults to VISUAL_QA_LLM/Flash with vision)
        
    Returns:
        Configured CrewAI Agent
    """
    if llm is None:
        llm = VISUAL_QA_LLM()
    
    return Agent(
        role="Visual Quality Inspector",
        goal="""Evaluate each slide screenshot for visual quality.
        Grade on a 0-100 scale across 5 criteria.
        Pass threshold is 95%.
        Identify specific issues that need fixing.
        Be thorough but fair in grading.""",
        backstory="""You are a presentation design expert with an eagle eye for detail.
        You've reviewed thousands of presentations for Fortune 500 companies and top 
        universities. You can instantly spot layout issues, typography problems, and
        visual imbalances. You're known for your constructive feedback that helps
        presentations go from good to exceptional. You hold high standards but 
        always explain exactly how to fix issues you find.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
    )


def create_qa_task(
    agent: Agent,
    presentation: GeneratedPresentation,
    slide_screenshots: List[str],  # Base64 encoded images
) -> Task:
    """
    Create a task for the Visual QA to grade slides.
    
    Args:
        agent: The Visual QA agent
        presentation: Generated presentation with HTML
        slide_screenshots: Base64 screenshots of rendered slides
        
    Returns:
        CrewAI Task for quality assessment
    """
    return Task(
        description=f"""Grade these {len(presentation.slides)} slides for visual quality.

## SLIDES TO EVALUATE
{', '.join([f'Slide {s.order}: {s.title}' for s in presentation.slides])}

## GRADING CRITERIA
1. Layout Quality (0-20)
2. Typography (0-20)
3. Content Visibility (0-20)
4. Visual Hierarchy (0-20)
5. Completeness (0-20)

## PASS THRESHOLD
Score >= 95% to pass

For each slide:
1. Evaluate the screenshot
2. Score each criterion
3. List any issues found
4. Provide specific fix suggestions
5. Mark as passed/failed

Return a complete QAReport.""",
        expected_output="""A QAReport containing:
- session_id
- slides: Array of QAResult for each slide
- average_score
- all_passed: true if ALL slides scored >= 95%
- total_iterations""",
        agent=agent,
        output_pydantic=QAReport,
    )


VISUAL_QA_CONFIG = {
    "role": "Visual Quality Inspector",
    "goal": "Grade slide quality and identify issues for fixing.",
    "backstory": "Expert with eagle eye for design issues.",
    "llm": "gemini/gemini-3-flash-preview",
    "thinking_level": "medium",
    "memory": True,
    "verbose": True,
    "pass_threshold": 95,
    "max_iterations": 3,
}
