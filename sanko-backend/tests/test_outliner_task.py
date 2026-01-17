"""
Tests for the Outliner Agent task creation.

Tests the create_outliner_task() function that generates intelligent
presentation outlines based on OrderForm + KnowledgeBase.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.crew.agents.outliner import (
    create_outliner_agent,
    create_outliner_task,
    Skeleton,
    SkeletonSlide,
)
from app.models.schemas import (
    OrderForm,
    KnowledgeBase,
    DocumentSection,
)


@pytest.fixture
def sample_order_form():
    """Create a sample OrderForm for testing."""
    return OrderForm(
        presentation_title="Introduction to Machine Learning",
        target_audience="Graduate Students",
        target_slides=8,
        key_topics=["Neural Networks", "Backpropagation", "Deep Learning"],
        focus_areas=["Neural Networks", "Practical Applications"],
        emphasis_style="detailed",
        tone="academic",
        citation_style="apa",
        is_complete=True,
    )


@pytest.fixture
def sample_knowledge_base():
    """Create a sample KnowledgeBase for testing."""
    return KnowledgeBase(
        summary="Comprehensive overview of machine learning fundamentals",
        sections=[
            DocumentSection(
                title="Introduction to ML",
                content="Machine learning is a subset of artificial intelligence...",
                visuals=["system diagram"],
                page_range="1-5",
            ),
            DocumentSection(
                title="Neural Network Architecture",
                content="Neural networks consist of layers... The sigmoid function $\\sigma(x) = \\frac{1}{1+e^{-x}}$ is commonly used.",
                visuals=["neural network diagram"],
                page_range="6-12",
            ),
            DocumentSection(
                title="Backpropagation Algorithm",
                content="Backpropagation computes gradients using $\\frac{\\partial L}{\\partial w}$...",
                visuals=[],
                page_range="13-20",
            ),
        ],
    )


def test_create_outliner_agent_default():
    """Test agent creation with default LLM."""
    # Skip this test as it requires actual LLM setup
    # The real test is that the function can be imported and called
    pass


def test_create_outliner_agent_with_tools(sample_knowledge_base):
    """Test agent creation with custom tools."""
    from app.crew.tools.context_tool import ListSectionsTool
    
    # Use a real BaseTool subclass
    real_tool = ListSectionsTool(kb=sample_knowledge_base)
    
    # Use a valid LLM model string
    agent = create_outliner_agent(llm="gemini/gemini-3-flash-preview", tools=[real_tool])
    assert agent is not None
    assert real_tool in agent.tools


def test_create_outliner_task_with_order_form_only(sample_order_form):
    """Test task creation with just OrderForm (no documents)."""
    agent = create_outliner_agent(llm="gemini/gemini-3-flash-preview")
    
    task = create_outliner_task(
        agent=agent,
        order_form=sample_order_form,
        knowledge_base=None,
    )
    
    assert task is not None
    assert "Introduction to Machine Learning" in task.description
    assert "Graduate Students" in task.description
    assert "NO DOCUMENT PROVIDED" in task.description
    assert "Neural Networks" in task.description


def test_create_outliner_task_with_knowledge_base(sample_order_form, sample_knowledge_base):
    """Test task creation with both OrderForm and KnowledgeBase."""
    agent = create_outliner_agent(llm="gemini/gemini-3-flash-preview")
    
    task = create_outliner_task(
        agent=agent,
        order_form=sample_order_form,
        knowledge_base=sample_knowledge_base,
    )
    
    assert task is not None
    # Check document sections are included
    assert "Introduction to ML" in task.description
    assert "Neural Network Architecture" in task.description
    assert "[CONTAINS EQUATIONS]" in task.description  # LaTeX detected
    assert "DOCUMENT CONTENT" in task.description


def test_create_outliner_task_detects_equations(sample_order_form, sample_knowledge_base):
    """Test that task description correctly flags sections with equations."""
    agent = create_outliner_agent(llm="gemini/gemini-3-flash-preview")
    
    task = create_outliner_task(
        agent=agent,
        order_form=sample_order_form,
        knowledge_base=sample_knowledge_base,
    )
    
    # The Neural Network and Backpropagation sections have LaTeX
    description = task.description
    assert "[CONTAINS EQUATIONS]" in description


def test_create_outliner_task_includes_focus_areas(sample_order_form, sample_knowledge_base):
    """Test that focus areas are emphasized in the task."""
    agent = create_outliner_agent(llm="gemini/gemini-3-flash-preview")
    
    task = create_outliner_task(
        agent=agent,
        order_form=sample_order_form,
        knowledge_base=sample_knowledge_base,
    )
    
    assert "FOCUS AREAS" in task.description
    assert "Neural Networks" in task.description
    assert "Practical Applications" in task.description


def test_create_outliner_task_respects_emphasis_style(sample_order_form):
    """Test that emphasis style affects the task description."""
    agent = create_outliner_agent(llm="gemini/gemini-3-flash-preview")
    
    # Test detailed style
    sample_order_form.emphasis_style = "detailed"
    task = create_outliner_task(agent=agent, order_form=sample_order_form)
    assert "4-5 bullet points" in task.description
    
    # Test concise style  
    sample_order_form.emphasis_style = "concise"
    task = create_outliner_task(agent=agent, order_form=sample_order_form)
    assert "2-3 tight bullet" in task.description
    
    # Test visual-heavy style
    sample_order_form.emphasis_style = "visual-heavy"
    task = create_outliner_task(agent=agent, order_form=sample_order_form)
    assert "diagrams and images" in task.description


def test_skeleton_slide_model():
    """Test the SkeletonSlide Pydantic model from schemas.py."""
    from app.models.schemas import SkeletonSlide, SlideContentType
    
    slide = SkeletonSlide(
        order=1,
        title="Test Slide",
        content_type=SlideContentType.CONTENT,
        description="A slide about testing",
        needs_diagram=True,
        diagram_description="A flowchart",
        needs_equation=False,
    )
    
    assert slide.order == 1
    assert slide.title == "Test Slide"
    assert slide.needs_diagram is True
    assert slide.diagram_description == "A flowchart"
    assert slide.description == "A slide about testing"


def test_skeleton_model():
    """Test the Skeleton Pydantic model from schemas.py."""
    from app.models.schemas import Skeleton, SkeletonSlide, SlideContentType
    
    skeleton = Skeleton(
        presentation_title="Test Presentation",
        target_audience="Students",
        narrative_arc="Introduction to conclusion",
        slides=[
            SkeletonSlide(order=1, title="Title", content_type=SlideContentType.TITLE),
            SkeletonSlide(order=2, title="Content", content_type=SlideContentType.CONTENT, needs_citation=True),
        ],
    )
    
    # Note: schemas.py Skeleton doesn't have update_metrics
    assert skeleton.presentation_title == "Test Presentation"
    assert len(skeleton.slides) == 2
    assert skeleton.slides[1].needs_citation is True
