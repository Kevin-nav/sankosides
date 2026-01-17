"""
Clarifier Agent

Purpose: Conversational negotiation to extract exact user requirements.
Model: Gemini Flash (low thinking for fast Q&A)

This agent implements the "Contract Negotiator" role:
- Engages in back-and-forth conversation until user is satisfied
- Locks in theme, citation style, tone, focus areas, and scope
- Outputs a structured OrderForm when complete

Key Feature: NOT limited to 3 questions - continues until satisfied.
"""

from crewai import Agent, Task
from typing import Optional

from app.models.schemas import OrderForm, KnowledgeBase
from app.clients.gemini.llm import CLARIFIER_LLM


# Enhanced system prompt with intelligent conversation flow
CLARIFIER_SYSTEM_PROMPT = """You are an expert presentation planning consultant helping users define their slide requirements.

## CRITICAL RULES (MUST FOLLOW - NO EXCEPTIONS)

### 1. DETECT THE MODE FIRST
Determine which mode you're in based on what the user has provided:

| Mode | Condition | Focus |
|------|-----------|-------|
| **DOCUMENT MODE** | User uploaded a PDF/document | Scope sections, ask about source exclusivity |
| **RESEARCH MODE** | No document, user has a topic | Define scope, depth of research needed |
| **HYBRID MODE** | Document + user wants external sources | Both document scoping AND research parameters |

### 2. DOCUMENT MODE FLOW
If the user uploads a document:
1. **Acknowledge immediately** - "I see you've uploaded [document]. I found these sections: [list]"
2. **Scope sections** - "Which sections would you like to focus on?"
3. **Ask source preference** - "Should I use content EXCLUSIVELY from this document, or can I supplement with external research?"
4. Then gather remaining requirements (audience, slide count, etc.)

### 3. RESEARCH MODE FLOW (No document)
If no document is provided:
1. **Clarify topic scope** - What specific aspects to cover?
2. **Understand depth** - Overview vs deep-dive?
3. **Academic standards** - Citation requirements, authoritative sources needed?
4. Then gather remaining requirements (audience, slide count, etc.)

### 4. NEVER RE-CONFIRM EXPLICIT STATEMENTS
If the user EXPLICITLY states something, lock it in silently:
- ❌ DON'T: "You said Harvard style. Is that correct?"
- ✅ DO: Silently record "harvard" and move to the NEXT missing piece

### 5. INTELLIGENT DEFAULTS
Apply these defaults automatically based on context:
| Context clue | Auto-set |
|--------------|----------|
| "university students", "academic", "research" | tone = "academic" |
| "startup", "pitch", "investors" | tone = "persuasive" |
| "harvard/apa/ieee/chicago" mentioned | citation_style = mentioned style |
| "only from this document" / "just the PDF" | source_type = "pdf_only" |
| "you can research" / "supplement" | source_type = "pdf_plus_research" |
| No document provided | source_type = "research_only" |

### 6. COMPLETION CHECKLIST
You are READY TO CONFIRM when you have ALL of these:
- ✅ Title/topic defined
- ✅ Target audience specified
- ✅ Slide count set (or user said "you decide")
- ✅ Focus areas/sections identified
- ✅ Source type determined (pdf_only / pdf_plus_research / research_only)
- ✅ Section scope set (if in DOCUMENT MODE)

When ALL items are checked, present ONE summary and ask "Ready to proceed?"

## INFORMATION TO GATHER

Required (must ask if missing):
- Presentation title/topic
- Target audience
- Number of slides (3-50)
- Focus areas/topics to cover
- Source preference (if document uploaded)

Optional (use defaults if not mentioned):
- Emphasis style: detailed, concise, visual-heavy (default: "detailed")
- Tone: academic, casual, technical, persuasive (default from context or "academic")
- Citation style: apa, ieee, harvard, chicago (default: "apa")
- References placement: distributed, last_slide (default: "last_slide")
- Theme: academic, modern, minimal, dark (default: "modern")

## RESPONSE FORMAT

**When gathering info**: Write naturally. Ask only what you don't know.

**Final confirmation** (ONCE, at the end):
Present a clean summary of ALL settings including source type, then ask: "Ready to proceed?"

**OrderForm output** (ONLY after user confirms):
```json
{
  "presentation_title": "...",
  "target_audience": "...",
  "target_slides": 10,
  "focus_areas": ["topic1", "topic2"],
  "key_topics": ["..."],
  "tone": "academic",
  "emphasis_style": "detailed",
  "citation_style": "apa",
  "references_placement": "last_slide",
  "theme_id": "modern",
  "special_requests": "",
  "is_complete": true
}
```

## KEY REMINDERS

- Document attached? → Acknowledge FIRST, scope sections, ask about source exclusivity
- No document? → Research mode - focus on topic scope and depth
- User stated something explicitly? → Don't ask again, just record it
- Have all required info? → ONE summary at the end, then hand off to next stage
"""



def create_clarifier_agent(llm=None, tools=None) -> Agent:
    """
    Create the Clarifier Agent (The Negotiator).
    
    This agent:
    - Engages in conversational Q&A (not limited to 3 questions!)
    - Gathers ALL presentation requirements including focus areas
    - Outputs a structured OrderForm when complete
    
    Args:
        llm: The LLM instance (defaults to CLARIFIER_LLM if not provided)
        tools: Optional list of tools for the agent (e.g., ReadSectionTool)
        
    Returns:
        Configured CrewAI Agent
    """
    if llm is None:
        llm = CLARIFIER_LLM()
    
    return Agent(
        role="Presentation Requirements Specialist",
        goal="""Gather presentation requirements efficiently through smart conversation.
        
        PRIORITIES:
        1. If documents are uploaded, acknowledge them FIRST and list sections found
        2. Never re-confirm what the user explicitly stated
        3. Use intelligent defaults for optional fields based on context
        4. Only output OrderForm after ONE final confirmation summary
        
        Required: title, audience, slide count, focus areas
        Optional (use defaults): emphasis style, tone, citation style, theme
        
        To respond to users, use your Final Answer - no special tool needed.
        Document tools are ONLY for reading source content, not for communication.""",
        backstory="""You are a presentation consultant who values efficiency and clarity.
        You're known for understanding users quickly without excessive back-and-forth.
        
        Your approach:
        - When users attach documents, you analyze them first before asking questions
        - You never ask for confirmation of something explicitly stated
        - You apply intelligent defaults (e.g., 'university students' → academic tone)
        - You bundle related questions to save time
        - You present ONE clean summary at the end, not piece-by-piece confirmations
        
        Document tools are for reading source material only - communicate via Final Answer.""",
        llm=llm,
        tools=tools or [],
        verbose=True,
        allow_delegation=False,
        memory=True,
    )


def create_clarification_task(
    agent: Agent, 
    user_input: str,
    knowledge_base: Optional[KnowledgeBase] = None,
    university_context: Optional["UniversityContext"] = None,
) -> Task:
    """
    Create a task for the Clarifier to process user input.
    
    Args:
        agent: The Clarifier agent
        user_input: The user's message
        knowledge_base: Optional extracted content from user documents
        university_context: Optional university context for institution-specific defaults
        
    Returns:
        CrewAI Task configured for clarification
    """
    context_injection = ""
    
    # Inject university context if available
    university_injection = ""
    if university_context:
        defaults = university_context.get_clarifier_defaults()
        university_injection = f"""
## UNIVERSITY-SPECIFIC DEFAULTS (AUTO-APPLIED)
The user is from **{university_context.university.name} ({university_context.university.short_name})**.

These settings are ALREADY LOCKED IN based on their institution - DO NOT ask about them:
- Citation style: **{university_context.university.default_citation_style.upper()}** (institution standard)
- Spelling: **{university_context.university.spelling_variant.title()} English**
- References: **{university_context.university.formatting_rules.reference_placement.replace('_', ' ')}**
- Tone: **academic** (institutional context)

You only need to ask about:
- Presentation title/topic
- Target audience
- Number of slides  
- Focus areas (what to emphasize)
- Emphasis style (if not obvious from context)
"""

    if knowledge_base:
        section_list = "\n".join([f"- {s.title}" for s in knowledge_base.sections])
        context_injection = f"""
## CONTEXT FROM USER DOCUMENTS
The user has uploaded documents. You MUST acknowledge this in your response.

**Document Summary:** {knowledge_base.summary}

**Sections Found:**
{section_list}

**YOUR FIRST RESPONSE MUST:**
1. Acknowledge the document ("I see you've uploaded a document about...")
2. List the key sections you found
3. If the user already specified sections to focus on, confirm you found them
4. If not specified, ask which sections should be the focus

Do NOT skip straight to asking about slide count or other details before addressing the document.
"""

    # Build defaults section based on whether university context is available
    if university_context:
        defaults_section = f"""
Optional (use university defaults below):
- [ ] Emphasis style → default: "detailed"
- [ ] Tone → LOCKED: "academic" (from {university_context.university.short_name})
- [ ] Citation style → LOCKED: "{university_context.university.default_citation_style}" (from {university_context.university.short_name})
- [ ] References placement → LOCKED: "{university_context.university.formatting_rules.reference_placement}"
- [ ] Theme → default: "modern"
"""
    else:
        defaults_section = """
Optional (use intelligent defaults if not mentioned):
- [ ] Emphasis style → default: "detailed"
- [ ] Tone → infer from context (students=academic, startup=persuasive) or default: "academic"
- [ ] Citation style → default: "apa" (unless specified)
- [ ] References placement → default: "last_slide"
- [ ] Theme → default: "modern"
- [ ] Any special requests
"""

    return Task(
        description=f"""Process this user message and continue gathering requirements:

USER MESSAGE: {user_input}
{university_injection}
{context_injection}
Your job is to:
1. Extract any information provided in this message
2. Identify what information is still missing
3. Ask follow-up questions for missing details
4. When all information is gathered, summarize and ask for confirmation

Required (must ask if missing):
- [ ] Presentation title/topic
- [ ] Target audience
- [ ] Number of slides
- [ ] Focus areas (what to emphasize)
{defaults_section}
Respond naturally and gather missing information.""",
        expected_output="""Either:
1. A conversational response asking clarifying questions, OR
2. A complete OrderForm JSON when the user has confirmed all details""",
        agent=agent,
        output_pydantic=OrderForm,  # Structured output when complete
    )


# Agent configuration as YAML-compatible dict (for reference)
CLARIFIER_CONFIG = {
    "role": "Presentation Requirements Specialist",
    "goal": "Gather complete presentation requirements through thorough conversation.",
    "backstory": "Expert consultant who never misses important details.",
    "llm": "gemini/gemini-3-flash-preview",
    "thinking_level": "low",
    "memory": True,
    "verbose": True,
}
