import pytest
from app.models.schemas import DocumentSection, KnowledgeBase

def test_document_section_model():
    section = DocumentSection(
        title="Introduction",
        content="This is the introduction.",
        visuals=["A diagram of the system"],
        page_range="1-2"
    )
    assert section.title == "Introduction"
    assert section.content == "This is the introduction."
    assert section.visuals == ["A diagram of the system"]
    assert section.page_range == "1-2"

def test_knowledge_base_model():
    section1 = DocumentSection(title="Section 1", content="Content 1")
    section2 = DocumentSection(title="Section 2", content="Content 2")
    
    kb = KnowledgeBase(
        summary="This is a summary of the document.",
        sections=[section1, section2]
    )
    
    assert kb.summary == "This is a summary of the document."
    assert len(kb.sections) == 2
    assert kb.sections[0].title == "Section 1"
    assert kb.get_section_titles() == ["Section 1", "Section 2"]

def test_knowledge_base_serialization():
    kb = KnowledgeBase(
        summary="Summary",
        sections=[DocumentSection(title="Title", content="Content")]
    )
    
    json_data = kb.model_dump()
    assert json_data["summary"] == "Summary"
    assert len(json_data["sections"]) == 1
    assert json_data["sections"][0]["title"] == "Title"
    
    restored_kb = KnowledgeBase(**json_data)
    assert restored_kb.summary == "Summary"
    assert restored_kb.sections[0].content == "Content"
