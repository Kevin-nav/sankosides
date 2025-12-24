import pytest
from unittest.mock import MagicMock
from app.crew.agents.clarifier import create_clarification_task, create_clarifier_agent
from app.models.schemas import KnowledgeBase, DocumentSection

def test_create_clarification_task_with_context():
    agent = create_clarifier_agent()
    kb = KnowledgeBase(
        summary="Calculus notes covering Limits.",
        sections=[DocumentSection(title="Limits", content="Limit laws...")]
    )
    
    task = create_clarification_task(agent, "Hi", knowledge_base=kb)
    
    assert "CONTEXT FROM USER DOCUMENTS" in task.description
    assert "Calculus notes covering Limits." in task.description
    assert "- Limits" in task.description

def test_create_clarification_task_without_context():
    agent = create_clarifier_agent()
    task = create_clarification_task(agent, "Hi")
    
    assert "CONTEXT FROM USER DOCUMENTS" not in task.description

def test_clarifier_agent_tool_registration():
    from app.crew.tools.context_tool import ReadSectionTool
    kb = KnowledgeBase(summary="S", sections=[])
    tool = ReadSectionTool(kb=kb)
    agent = create_clarifier_agent(tools=[tool])
    assert tool in agent.tools


