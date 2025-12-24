import pytest
from app.crew.flows.slide_generation import FlowState
from app.models.schemas import KnowledgeBase, DocumentSection

def test_flow_state_knowledge_base():
    # Test initialization with knowledge_base
    kb = KnowledgeBase(
        summary="Test Summary",
        sections=[DocumentSection(title="S1", content="C1")]
    )
    
    state = FlowState(session_id="test-session", knowledge_base=kb)
    
    assert state.knowledge_base is not None
    assert state.knowledge_base.summary == "Test Summary"
    
    # Test serialization to DB dict
    db_dict = state.to_db_dict()
    assert "knowledge_base" in db_dict
    assert db_dict["knowledge_base"]["summary"] == "Test Summary"
    
    # Test deserialization from DB dict
    restored_state = FlowState.from_db(db_dict)
    assert restored_state.knowledge_base is not None
    assert restored_state.knowledge_base.summary == "Test Summary"
    assert restored_state.knowledge_base.sections[0].title == "S1"

def test_flow_state_knowledge_base_default_none():
    state = FlowState(session_id="test-session")
    assert state.knowledge_base is None
    
    db_dict = state.to_db_dict()
    assert db_dict.get("knowledge_base") is None
