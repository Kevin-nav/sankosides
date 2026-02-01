"""
Planner Agent

Purpose: Create full slide content with placeholders for assets.
Model: Gemini PRO (high thinking for deep content planning)

This agent is the "Content Architect":
- Takes the approved skeleton and user preferences (OrderForm)
- Generates FULL content for each slide (not just outlines)
- Creates placeholders for equations, diagrams, citations, images
- Respects focus_areas and emphasis_style from OrderForm
- Outputs PlannedContent ready for the Refiner
"""

from crewai import Agent, Task
from crewai.tools import BaseTool
from typing import Optional, List

from app.models.schemas import (
    OrderForm,
    Skeleton,
    PlannedContent,
    PlannedSlide,
    SlideContentType,
)
from app.clients.gemini.llm import PLANNER_LLM


PLANNER_SYSTEM_PROMPT = """You are an expert academic content writer and presentation architect.

YOUR MISSION:
Transform a presentation skeleton into COMPLETE slide content, respecting the user's preferences.

## INPUTS YOU WILL RECEIVE
1. **Skeleton**: Slide structure with titles and flags for what's needed
2. **OrderForm**: User preferences including:
   - focus_areas: Topics to emphasize
   - emphasis_style: "detailed", "concise", or "visual-heavy"
   - tone: academic, casual, technical, or persuasive
   - citation_style: For formatting references
   - references_placement: Where citations go
   - special_requests: Custom requirements

## YOUR RESPONSIBILITIES

### 1. Content Generation (CRITICAL)
For EACH slide, write COMPLETE content:
- Full bullet points with substantive information (not placeholders!)
- Apply the correct emphasis_style:
  - "detailed": 4-5 substantial bullet points with explanations
  - "concise": 2-3 tight bullet points
  - "visual-heavy": 1-2 bullets, prioritize diagram/image needs
- Apply the correct tone throughout

### 2. Academic Elements
When a slide needs citations:
- Add `citation_queries`: Search terms for finding relevant papers
- Example: ["machine learning climate prediction", "neural networks weather forecasting"]

### 3. Research-Backed Claims (NEW - CRITICAL)
For claims that need academic support, add `research_needs`:
- Each research need specifies a claim, search query, and intent
- Intent types: "statistic", "definition", "methodology", "finding", "common_fact"
- Mark `is_common_knowledge: true` for widely-known facts that don't need deep research

Example research_needs:
```json
[
  {"claim": "AI can predict weather with 90% accuracy", "query": "AI weather prediction accuracy", "intent": "statistic", "is_common_knowledge": false},
  {"claim": "Machine learning uses neural networks", "query": "", "intent": "common_fact", "is_common_knowledge": true}
]
```

RULE: Only add research_needs for claims that:
1. Contain specific statistics or numbers
2. Make bold assertions about effectiveness or performance
3. Describe methodologies or findings that should be attributed
4. Are NOT common knowledge (e.g., "water boils at 100°C" needs no research)

When a slide needs equations:
- Add `equation_placeholder`: Description of what equation is needed
- Example: "Linear regression formula: y = mx + b with explanation"

When a slide needs diagrams:
- Add `diagram_placeholder`: Description of what diagram is needed
- Example: "Flowchart showing data preprocessing pipeline"

When a slide needs images:
- Add `image_query`: Search term for finding relevant images
- Example: "satellite imagery climate change visualization"

### 4. Focus Areas
If focus_areas says ["machine learning", "sustainability"]:
- These topics should be MORE detailed
- Other topics can be briefer
- Explicitly emphasize these in speaker notes

### 4. Template Selection
Based on content, suggest the best template_type:
- "title": Opening slide
- "content": Standard bullet points
- "diagram": Diagram-focused layout
- "equation": Math-focused layout
- "image": Image-focused layout
- "two_column": Split layout
- "quote": Quote slide
- "conclusion": Closing slide

### 5. Speaker Notes
If include_speaker_notes is true:
- Add substantial speaker notes for each slide
- Include talking points not on the slide
- Add timing suggestions if relevant

## OUTPUT FORMAT

Return a PlannedContent object with:
- presentation_title
- target_audience
- theme_id
- citation_style
- slides: List of PlannedSlide, each with:
  - order, title, content_type
  - bullet_points (FULL content!)
  - equation_placeholder (if needed)
  - diagram_placeholder (if needed)
  - citation_queries (if needed)
  - image_query (if needed)
  - research_needs (for claims needing academic backing)
  - template_type
  - speaker_notes (if requested)

## QUALITY STANDARDS

1. NEVER leave bullet points empty or vague
2. Each slide should have a clear, focused purpose
3. Content should flow logically from slide to slide
4. Focus areas should be noticeably more detailed
5. Respect the target slide count from the skeleton
"""


def create_planner_agent(llm=None, tools: Optional[List[BaseTool]] = None) -> Agent:
    """
    Create the Planner Agent (The Content Architect).
    
    This agent uses Gemini PRO with HIGH thinking for deep content generation.
    
    Args:
        llm: The LLM instance (defaults to PLANNER_LLM/PRO if not provided)
        tools: Optional list of tools (e.g., AcademicSearchTool)
        
    Returns:
        Configured CrewAI Agent
    """
    if llm is None:
        llm = PLANNER_LLM()
    
    agent_kwargs = {
        "role": "Content Architect & Academic Writer",
        "goal": """Transform the presentation skeleton into COMPLETE slide content.
        Write full, substantive bullet points - never placeholders or outlines.
        Respect the user's focus_areas (emphasize these topics more).
        Apply the correct emphasis_style (detailed/concise/visual-heavy).
        Identify where citations, equations, diagrams, and images are needed.
        Output a complete PlannedContent ready for refinement.""",
        "backstory": """You are a PhD-level researcher and professional presentation writer
        with expertise across multiple academic disciplines. You've written thousands of 
        presentations for conferences, lectures, and business meetings. You understand 
        how to transform complex topics into clear, engaging slides. You excel at 
        adapting content for different audiences - from students to executives to 
        expert panels. You know exactly when a diagram would explain better than words,
        and you understand academic citation requirements deeply.""",
        "llm": llm,
        "verbose": True,
        "allow_delegation": False,
        "memory": True,
    }
    
    if tools:
        agent_kwargs["tools"] = tools
    
    return Agent(**agent_kwargs)


def create_planning_task(
    agent: Agent,
    skeleton: Skeleton,
    order_form: OrderForm,
    university_context: Optional["UniversityContext"] = None,
) -> Task:
    """
    Create a task for the Planner to generate content.
    
    Args:
        agent: The Planner agent
        skeleton: Approved presentation structure
        order_form: User preferences from Clarifier
        university_context: Optional university context for formatting rules
        
    Returns:
        CrewAI Task for content planning
    """
    # Build context from skeleton
    slides_context = "\n".join([
        f"Slide {s.order}: {s.title} ({s.content_type.value})"
        f"\n  - {s.description}"
        f"\n  - Needs diagram: {s.needs_diagram}" + (f" - {s.diagram_description}" if s.diagram_description else "")
        + f"\n  - Needs equation: {s.needs_equation}" + (f" - {s.equation_description}" if s.equation_description else "")
        + f"\n  - Needs citation: {s.needs_citation}" + (f" - {s.citation_topic}" if s.citation_topic else "")
        + f"\n  - Needs image: {s.needs_image}" + (f" - {s.image_description}" if s.image_description else "")
        for s in skeleton.slides
    ])
    
    # Build university formatting rules if available
    formatting_rules = ""
    department_suggestions = ""
    if university_context:
        formatting_rules = university_context.get_agent_prompt_injection()
        
        # Add department-specific suggestions
        if university_context.department:
            dept = university_context.department
            if dept.common_diagram_types:
                diagram_types = ", ".join(dept.common_diagram_types[:5])
                department_suggestions += f"\n**Suggested Diagrams for {dept.name}:** {diagram_types}"
            if dept.common_equation_domains:
                equation_domains = ", ".join(dept.common_equation_domains[:5])
                department_suggestions += f"\n**Common Equation Domains:** {equation_domains}"
    
    return Task(
        description=f"""Create COMPLETE slide content for this presentation.

## PRESENTATION SKELETON
Title: {skeleton.presentation_title}
Target Audience: {skeleton.target_audience}
Narrative: {skeleton.narrative_arc}

### Slides to Write:
{slides_context}

## USER PREFERENCES (OrderForm)
- **Tone**: {order_form.tone}
- **Emphasis Style**: {order_form.emphasis_style}
- **Focus Areas**: {', '.join(order_form.focus_areas) if order_form.focus_areas else 'None specified'}
- **Citation Style**: {order_form.citation_style}
- **References Placement**: {order_form.references_placement}
- **Include Speaker Notes**: {order_form.include_speaker_notes}
- **Special Requests**: {order_form.special_requests or 'None'}
{formatting_rules}
{department_suggestions}

## YOUR TASK
1. Write FULL content for EVERY slide (not just outlines!)
2. Apply emphasis_style: {order_form.emphasis_style}
3. Emphasize focus_areas more heavily: {order_form.focus_areas}
4. Add placeholders for assets that the Refiner will fill
5. Suggest template_type for each slide
6. Add speaker_notes if requested
7. Follow all institution formatting rules above (if specified)
8. Identify claims needing research backing (add research_needs)

## OUTPUT FORMAT
Return ONLY a valid JSON object (no schema, no explanation) with this structure:
{{
  "presentation_title": "string",
  "target_audience": "string",
  "theme_id": "string",
  "citation_style": "string",
  "slides": [
    {{
      "order": 1,
      "title": "Slide Title",
      "content_type": "content|title|diagram|equation|image|quote|two_column|section|overview|conclusion",
      "bullet_points": ["Full bullet point 1", "Full bullet point 2"],
      "equation_placeholder": "Description of equation needed or null",
      "diagram_placeholder": "Description of diagram needed or null",
      "citation_queries": ["search term 1", "search term 2"],
      "image_query": "image search term or null",
      "research_needs": [
        {{"claim": "Specific claim needing backing", "query": "search query", "intent": "statistic|definition|methodology|finding|common_fact", "is_common_knowledge": false}}
      ],
      "speaker_notes": "Speaker notes or null",
      "template_type": "content|title|diagram|equation|image|two_column|quote|conclusion"
    }}
  ]
}}

IMPORTANT: Output ONLY the JSON object. Do not include any schema definition, explanation, or markdown formatting.""",
        expected_output="""A JSON object with presentation_title, target_audience, theme_id, citation_style, and slides array. 
Each slide has: order, title, content_type, bullet_points (with full content), and optional placeholders.
Output ONLY the JSON - no explanation, no schema, no markdown.""",
        agent=agent,
        # Note: We intentionally do NOT use output_pydantic here because it causes
        # some LLMs (especially Gemini) to output the schema definition before the actual data.
        # Our _parse_planned_content function handles robust JSON extraction instead.
    )


# Agent configuration as YAML-compatible dict
PLANNER_CONFIG = {
    "role": "Content Architect & Academic Writer",
    "goal": "Transform skeleton into complete slide content with asset placeholders.",
    "backstory": "PhD-level researcher with expertise in creating academic presentations.",
    "llm": "gemini/gemini-3-pro-preview",
    "thinking_level": "high",
    "memory": True,
    "verbose": True,
}
