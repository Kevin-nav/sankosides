import pytest
import asyncio
from unittest.mock import patch
from app.models.schemas import KnowledgeBase, DocumentSection


def test_generator_has_element_tree_feature_flag():
    from app.core.config import settings

    assert hasattr(settings, "enable_element_tree_pipeline")
    assert hasattr(settings, "enable_element_tree_canvas")
    assert hasattr(settings, "enable_element_tree_export")


def test_legacy_html_generation_still_works_when_flag_disabled(monkeypatch):
    pytest.importorskip("crewai")

    from app.core.config import settings
    from app.crew.flows.slide_generation import SlideGenerationFlow
    from app.models.schemas import RefinedSlide, SlideContentType
    from app.models.slide_elements import SlideElementTree, SlideElement, TextContent, TextRun
    from app.themes import get_theme, UniversityBranding
    import app.templates.html_generator as html_generator

    flow = SlideGenerationFlow(session_id="test-session")
    refined = RefinedSlide(
        order=1,
        title="Fallback test",
        content_type=SlideContentType.CONTENT,
        bullet_points=["A"],
        element_tree=SlideElementTree(
            slide_id="slide-1",
            order=1,
            layout_id="content_bullets",
            elements=[
                SlideElement(
                    id="title",
                    type="text",
                    x=5,
                    y=5,
                    width=90,
                    height=12,
                    z_index=1,
                    content=TextContent(type="text", runs=[TextRun(text="From tree", size=40)]),
                )
            ],
        ),
    )

    monkeypatch.setattr(settings, "enable_element_tree_pipeline", False)

    async def fake_generate_slide_html_with_db_template(**_kwargs):
        return "<html><body>legacy template path</body></html>"

    def fake_element_tree_to_html(*_args, **_kwargs):
        return "<html><body>element tree path</body></html>"

    monkeypatch.setattr(
        html_generator,
        "generate_slide_html_with_db_template",
        fake_generate_slide_html_with_db_template,
    )
    monkeypatch.setattr(html_generator, "element_tree_to_html", fake_element_tree_to_html)

    generated = asyncio.run(
        flow._generate_slide_html_with_db_template(
            refined=refined,
            theme=get_theme("modern"),
            branding=UniversityBranding(),
            slide_number=1,
            total_slides=1,
            layout_style="default",
        )
    )

    assert "legacy template path" in generated.rendered_html


def test_run_synthesis_success():
    pytest.importorskip("crewai")

    from app.crew.flows.slide_generation import SlideGenerationFlow, FlowStatus

    # Setup
    flow = SlideGenerationFlow(session_id="test-session")
    file_paths = ["file1.pdf", "file2.pdf"]
    
    # Mock data
    kb1 = KnowledgeBase(
        summary="Summary 1",
        sections=[DocumentSection(title="S1", content="C1")]
    )
    kb2 = KnowledgeBase(
        summary="Summary 2",
        sections=[DocumentSection(title="S2", content="C2")]
    )
    
    # Mock SynthesisTool._run
    # We mock it at the class level or instance level where it's used in the flow
    with patch('app.crew.flows.slide_generation.SynthesisTool') as MockTool:
        mock_tool_instance = MockTool.return_value
        mock_tool_instance._run.side_effect = [kb1, kb2]
        
        # Run
        result = asyncio.run(flow.run_synthesis(file_paths))
        
        # Assertions
        assert flow.state.status == FlowStatus.AWAITING_CLARIFICATION
        assert flow.state.knowledge_base is not None
        assert len(flow.state.knowledge_base.sections) == 2
        assert "Summary 1" in flow.state.knowledge_base.summary
        assert "Summary 2" in flow.state.knowledge_base.summary
        assert result == flow.state.knowledge_base
        assert mock_tool_instance._run.call_count == 2

def test_run_synthesis_with_error():
    pytest.importorskip("crewai")

    from app.crew.flows.slide_generation import SlideGenerationFlow, FlowStatus

    flow = SlideGenerationFlow(session_id="test-session")
    file_paths = ["error.pdf"]
    
    with patch('app.crew.flows.slide_generation.SynthesisTool') as MockTool:
        mock_tool_instance = MockTool.return_value
        mock_tool_instance._run.return_value = "Error: Something went wrong"
        
        # Run
        result = asyncio.run(flow.run_synthesis(file_paths))
        
        # Assertions - should continue but result in empty sections if all failed
        assert len(result.sections) == 0
        assert flow.state.status == FlowStatus.AWAITING_CLARIFICATION
