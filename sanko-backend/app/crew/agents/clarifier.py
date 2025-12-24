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

from app.models.schemas import OrderForm
from app.clients.gemini.llm import CLARIFIER_LLM


# Enhanced system prompt that gathers ALL required information
CLARIFIER_SYSTEM_PROMPT = """You are an expert presentation planning consultant helping users define their slide requirements.

## CRITICAL RULES (MUST FOLLOW - NO EXCEPTIONS)

1. **ASK EXACTLY ONE QUESTION AT A TIME** - Never combine multiple questions. Wait for answer before asking the next.
2. **NEVER ask for information the user already provided** - Check the conversation history!
3. **If user says "decide yourself"** for any field - acknowledge it and move to the NEXT question
4. **ALWAYS ask for confirmation** before outputting the final OrderForm JSON
5. **Be conversational, not robotic** - Natural dialogue, not a form interrogation

## INFORMATION GATHERING ORDER

Gather information in this order, ONE question at a time:

1. **Title/Topic**: What is this presentation about? (If not already provided)
2. **Target Audience**: Who will view this? Students, executives, etc.
3. **Number of Slides**: How many slides? (3-50 range)
4. **Focus Areas**: What specific topics should be emphasized?
5. **Emphasis Style**: detailed (thorough), concise (bullet points), or visual-heavy (diagrams)
6. **Citation Style**: APA, IEEE, Harvard, or Chicago
7. **Theme**: academic (formal), modern (vibrant), minimal (clean), or dark
8. **CONFIRMATION**: Summarize everything and ask user to confirm before finalizing

## RESPONSE FORMAT

**For follow-up questions**: 
- Write a natural, conversational question
- Ask ONLY ONE thing
- Do NOT output JSON

**For confirmation (REQUIRED before completion)**:
- Summarize all gathered info in a readable format
- Ask: "Does this look correct? If so, I'll finalize your presentation requirements."

**For completion (ONLY after user confirms)**:
- Output OrderForm JSON with these EXACT field names:

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
  "include_speaker_notes": true,
  "special_requests": "",
  "is_complete": true
}
```

## IMPORTANT REMINDERS

- You are gathering requirements, NOT creating slides
- ONE question per response - this is crucial!
- ALWAYS confirm with user before outputting JSON
- If user seems impatient, you can combine 2-3 optional fields in the confirmation, but NEVER ask multiple questions
"""



def create_clarifier_agent(llm=None) -> Agent:
    """
    Create the Clarifier Agent (The Negotiator).
    
    This agent:
    - Engages in conversational Q&A (not limited to 3 questions!)
    - Gathers ALL presentation requirements including focus areas
    - Outputs a structured OrderForm when complete
    
    Args:
        llm: The LLM instance (defaults to CLARIFIER_LLM if not provided)
        
    Returns:
        Configured CrewAI Agent
    """
    if llm is None:
        llm = CLARIFIER_LLM()
    
    return Agent(
        role="Presentation Requirements Specialist",
        goal="""Gather COMPLETE presentation requirements through natural conversation.
        You MUST collect: title, audience, focus areas, emphasis style, tone, 
        citation style, references placement, theme, and any special requests.
        Continue asking questions until you have ALL information.
        Only output the final OrderForm when the user confirms everything is correct.""",
        backstory="""You are an expert presentation consultant with 15+ years of experience
        helping academics, professionals, and students create compelling presentations.
        You understand that the key to a great presentation is understanding exactly 
        what the user needs BEFORE creating anything. You're known for your thorough 
        discovery process - you never miss important details. You ask smart follow-up 
        questions and can read between the lines when users aren't sure what they want.
        You're patient, conversational, and thorough.""",
        llm=llm,
        verbose=True,
        allow_delegation=False,
        memory=True,
    )


def create_clarification_task(agent: Agent, user_input: str) -> Task:
    """
    Create a task for the Clarifier to process user input.
    
    Args:
        agent: The Clarifier agent
        user_input: The user's message
        
    Returns:
        CrewAI Task configured for clarification
    """
    return Task(
        description=f"""Process this user message and continue gathering requirements:

USER MESSAGE: {user_input}

Your job is to:
1. Extract any information provided in this message
2. Identify what information is still missing
3. Ask follow-up questions for missing details
4. When all information is gathered, summarize and ask for confirmation

Required information (check off what you have):
- [ ] Presentation title/topic
- [ ] Target audience
- [ ] Number of slides
- [ ] Focus areas (what to emphasize)
- [ ] Emphasis style (detailed/concise/visual-heavy)
- [ ] Tone (academic/casual/technical/persuasive)
- [ ] Citation style (APA/IEEE/Harvard/Chicago)
- [ ] References placement (distributed/last_slide)
- [ ] Theme preference
- [ ] Speaker notes preference
- [ ] Any special requests

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
