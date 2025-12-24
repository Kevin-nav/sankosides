"""
Tests for Clarifier Conversation Memory

These tests verify that the clarifier agent properly:
1. Tracks conversation history
2. Extracts information from user messages
3. Does not ask for info already provided
4. Handles "decide yourself" requests
"""

import pytest
from datetime import datetime

from app.models.schemas import (
    GatheredInfo,
    ClarificationMessage,
    OrderForm,
)
from app.crew.flows.slide_generation import (
    FlowState,
    FlowStatus,
    SlideGenerationFlow,
)




class TestGatheredInfo:
    """Test the GatheredInfo model for tracking conversation state."""
    
    def test_initial_state_is_empty(self):
        """GatheredInfo should start with no fields gathered."""
        info = GatheredInfo()
        
        assert info.has_title is False
        assert info.has_audience is False
        assert info.has_slide_count is False
        assert info.has_focus_areas is False
        assert info.title is None
        assert info.audience is None
        assert info.slide_count is None
        assert len(info.focus_areas) == 0
    
    def test_get_missing_required_all_missing(self):
        """When nothing is gathered, all required fields should be missing."""
        info = GatheredInfo()
        missing = info.get_missing_required()
        
        assert len(missing) == 4
        assert "presentation title or topic" in missing
        assert "target audience" in missing
        assert "number of slides" in missing
        assert "key focus areas or topics to cover" in missing
    
    def test_get_missing_required_partial(self):
        """Partial gathering should show remaining required fields."""
        info = GatheredInfo()
        info.title = "AI Agents in 2025"
        info.has_title = True
        info.audience = "university students"
        info.has_audience = True
        
        missing = info.get_missing_required()
        
        assert len(missing) == 2
        assert "number of slides" in missing
        assert "key focus areas or topics to cover" in missing
        assert "presentation title or topic" not in missing
        assert "target audience" not in missing
    
    def test_get_missing_required_with_agent_decide(self):
        """When user asks agent to decide, it should count as handled."""
        info = GatheredInfo()
        info.let_agent_decide_title = True
        info.has_title = True  # Marked as handled
        info.audience = "students"
        info.has_audience = True
        info.slide_count = 10
        info.has_slide_count = True
        info.focus_areas = ["AI impact"]
        info.has_focus_areas = True
        
        missing = info.get_missing_required()
        
        assert len(missing) == 0
    
    def test_is_complete_enough(self):
        """is_complete_enough should return True when all required fields are present."""
        info = GatheredInfo()
        assert info.is_complete_enough() is False
        
        info.title = "Test"
        info.has_title = True
        info.audience = "students"
        info.has_audience = True
        info.slide_count = 10
        info.has_slide_count = True
        info.focus_areas = ["Topic 1"]
        info.has_focus_areas = True
        
        assert info.is_complete_enough() is True
    
    def test_get_missing_optional(self):
        """Optional fields should be tracked separately."""
        info = GatheredInfo()
        missing = info.get_missing_optional()
        
        assert "emphasis style" in " ".join(missing).lower()
        assert "tone" in " ".join(missing).lower()
        assert "citation style" in " ".join(missing).lower()
        assert "theme" in " ".join(missing).lower()


class TestClarificationMessage:
    """Test the ClarificationMessage model."""
    
    def test_create_user_message(self):
        """User messages should be created correctly."""
        msg = ClarificationMessage(
            role="user",
            content="I want a presentation about AI"
        )
        
        assert msg.role == "user"
        assert msg.content == "I want a presentation about AI"
        assert isinstance(msg.timestamp, datetime)
    
    def test_create_assistant_message(self):
        """Assistant messages should be created correctly."""
        msg = ClarificationMessage(
            role="assistant",
            content="What is your target audience?"
        )
        
        assert msg.role == "assistant"
        assert msg.content == "What is your target audience?"


class TestFlowStateConversationTracking:
    """Test conversation tracking in FlowState."""
    
    def test_initial_state_has_empty_history(self):
        """New FlowState should have empty conversation history."""
        state = FlowState()
        
        assert len(state.conversation_history) == 0
        assert state.gathered_info is None
    
    def test_conversation_history_can_store_messages(self):
        """Conversation history should store messages."""
        state = FlowState()
        
        state.conversation_history.append(ClarificationMessage(
            role="user",
            content="I want 10 slides about ML"
        ))
        state.conversation_history.append(ClarificationMessage(
            role="assistant", 
            content="Who is your target audience?"
        ))
        
        assert len(state.conversation_history) == 2
        assert state.conversation_history[0].role == "user"
        assert state.conversation_history[1].role == "assistant"


class TestInfoExtraction:
    """Test the _extract_info_from_message helper."""
    
    def setup_method(self):
        """Create a flow for testing."""
        self.flow = SlideGenerationFlow()
        self.flow.state.gathered_info = GatheredInfo()
    
    def test_extract_audience_students(self):
        """Should extract 'university students' as audience."""
        self.flow._extract_info_from_message("This is for university students")
        
        assert self.flow.state.gathered_info.has_audience is True
        assert "students" in self.flow.state.gathered_info.audience.lower()
    
    def test_extract_audience_executives(self):
        """Should extract 'executives' as audience."""
        self.flow._extract_info_from_message("Presenting to executives")
        
        assert self.flow.state.gathered_info.has_audience is True
        assert "executives" in self.flow.state.gathered_info.audience.lower()
    
    def test_extract_slide_count(self):
        """Should extract slide count from message."""
        self.flow._extract_info_from_message("I need about 12 slides")
        
        assert self.flow.state.gathered_info.has_slide_count is True
        assert self.flow.state.gathered_info.slide_count == 12
    
    def test_extract_slide_count_range(self):
        """Should extract slide count from range (takes number before 'slides')."""
        self.flow._extract_info_from_message("Around 8-10 slides please")
        
        assert self.flow.state.gathered_info.has_slide_count is True
        # The regex matches "10 slides" so we get 10
        assert self.flow.state.gathered_info.slide_count == 10
    
    def test_extract_citation_style_harvard(self):
        """Should extract Harvard citation style."""
        self.flow._extract_info_from_message("Use harvard citation style")
        
        assert self.flow.state.gathered_info.has_citation_style is True
        assert self.flow.state.gathered_info.citation_style == "harvard"
    
    def test_extract_citation_style_apa(self):
        """Should extract APA citation style."""
        self.flow._extract_info_from_message("APA format please")
        
        assert self.flow.state.gathered_info.has_citation_style is True
        assert self.flow.state.gathered_info.citation_style == "apa"
    
    def test_extract_references_placement_last_slide(self):
        """Should extract references placement at end."""
        self.flow._extract_info_from_message("Put references at the last slide")
        
        assert self.flow.state.gathered_info.has_references_placement is True
        assert self.flow.state.gathered_info.references_placement == "last_slide"
    
    def test_extract_decide_yourself_title(self):
        """Should detect 'decide yourself' for title."""
        self.flow._extract_info_from_message("decide the title yourself")
        
        assert self.flow.state.gathered_info.let_agent_decide_title is True
        assert self.flow.state.gathered_info.has_title is True
    
    def test_extract_decide_yourself_theme(self):
        """Should detect 'decide yourself' for theme."""
        self.flow._extract_info_from_message("you can pick the theme")
        
        assert self.flow.state.gathered_info.let_agent_decide_theme is True
        assert self.flow.state.gathered_info.has_theme is True
    
    def test_extract_decide_up_to_you(self):
        """Should detect 'up to you' pattern."""
        self.flow._extract_info_from_message("the title is up to you")
        
        assert self.flow.state.gathered_info.let_agent_decide_title is True
    
    def test_extract_emphasis_detailed(self):
        """Should extract detailed emphasis style."""
        self.flow._extract_info_from_message("I want thorough, detailed slides")
        
        assert self.flow.state.gathered_info.has_emphasis_style is True
        assert self.flow.state.gathered_info.emphasis_style == "detailed"
    
    def test_extract_emphasis_concise(self):
        """Should extract concise emphasis style."""
        self.flow._extract_info_from_message("Keep it brief with bullet points")
        
        assert self.flow.state.gathered_info.has_emphasis_style is True
        assert self.flow.state.gathered_info.emphasis_style == "concise"
    
    def test_extract_emphasis_visual(self):
        """Should extract visual-heavy emphasis style."""
        self.flow._extract_info_from_message("Lots of diagrams and images please")
        
        assert self.flow.state.gathered_info.has_emphasis_style is True
        assert self.flow.state.gathered_info.emphasis_style == "visual-heavy"
    
    def test_extract_tone_academic(self):
        """Should extract academic tone."""
        self.flow._extract_info_from_message("Keep it formal and academic")
        
        assert self.flow.state.gathered_info.has_tone is True
        assert self.flow.state.gathered_info.tone == "academic"
    
    def test_extract_tone_casual(self):
        """Should extract casual tone."""
        self.flow._extract_info_from_message("Make it casual and friendly")
        
        assert self.flow.state.gathered_info.has_tone is True
        assert self.flow.state.gathered_info.tone == "casual"
    
    def test_extract_theme_dark(self):
        """Should extract dark theme."""
        self.flow._extract_info_from_message("Use dark mode theme")
        
        assert self.flow.state.gathered_info.has_theme is True
        assert self.flow.state.gathered_info.theme == "dark"
    
    def test_extract_theme_minimal(self):
        """Should extract minimal theme."""
        self.flow._extract_info_from_message("I prefer a minimalist look")
        
        assert self.flow.state.gathered_info.has_theme is True
        assert self.flow.state.gathered_info.theme == "minimal"
    
    def test_extract_topic_about_pattern(self):
        """Should extract topic from 'about X' pattern."""
        self.flow._extract_info_from_message("a presentation about machine learning trends")
        
        assert self.flow.state.gathered_info.has_title is True
        assert "machine learning" in self.flow.state.gathered_info.title.lower()


class TestFormatHelpers:
    """Test the formatting helper methods."""
    
    def setup_method(self):
        """Create a flow for testing."""
        self.flow = SlideGenerationFlow()
        self.flow.state.gathered_info = GatheredInfo()
    
    def test_format_conversation_history_empty(self):
        """Empty history should return placeholder text."""
        result = self.flow._format_conversation_history()
        
        assert "start of the conversation" in result.lower()
    
    def test_format_conversation_history_with_messages(self):
        """Should format messages with role labels."""
        self.flow.state.conversation_history.append(ClarificationMessage(
            role="user",
            content="I want a presentation"
        ))
        self.flow.state.conversation_history.append(ClarificationMessage(
            role="assistant",
            content="What topic?"
        ))
        
        result = self.flow._format_conversation_history()
        
        assert "USER:" in result
        assert "ASSISTANT:" in result
        assert "I want a presentation" in result
        assert "What topic?" in result
    
    def test_format_gathered_info_empty(self):
        """Empty gathered info should return placeholder text."""
        result = self.flow._format_gathered_info()
        
        assert "nothing gathered" in result.lower()
    
    def test_format_gathered_info_with_data(self):
        """Should format gathered info with labels."""
        self.flow.state.gathered_info.title = "AI Presentation"
        self.flow.state.gathered_info.audience = "students"
        self.flow.state.gathered_info.slide_count = 10
        
        result = self.flow._format_gathered_info()
        
        assert "AI Presentation" in result
        assert "students" in result
        assert "10" in result
    
    def test_format_gathered_info_agent_decide(self):
        """Should indicate when agent will decide."""
        self.flow.state.gathered_info.let_agent_decide_title = True
        
        result = self.flow._format_gathered_info()
        
        assert "wants you to decide" in result.lower() or "user wants" in result.lower()
    
    def test_format_list(self):
        """Should format list items with bullets."""
        items = ["item 1", "item 2", "item 3"]
        result = self.flow._format_list(items)
        
        assert "- item 1" in result
        assert "- item 2" in result
        assert "- item 3" in result


class TestMergeGatheredInfo:
    """Test merging gathered info into OrderForm."""
    
    def setup_method(self):
        """Create a flow for testing."""
        self.flow = SlideGenerationFlow()
        self.flow.state.gathered_info = GatheredInfo()
    
    def test_merge_fills_missing_fields(self):
        """Merge should fill in fields missing from OrderForm."""
        self.flow.state.gathered_info.title = "My Title"
        self.flow.state.gathered_info.audience = "developers"
        self.flow.state.gathered_info.slide_count = 15
        self.flow.state.gathered_info.focus_areas = ["topic 1", "topic 2"]
        self.flow.state.gathered_info.citation_style = "ieee"
        
        order_form = OrderForm()  # Empty form
        merged = self.flow._merge_gathered_info(order_form)
        
        assert merged.presentation_title == "My Title"
        assert merged.target_audience == "developers"
        assert merged.target_slides == 15
        assert merged.focus_areas == ["topic 1", "topic 2"]
        assert merged.citation_style == "ieee"
    
    def test_merge_respects_existing_values(self):
        """Merge should not overwrite existing non-default values."""
        self.flow.state.gathered_info.title = "Gathered Title"
        
        order_form = OrderForm(presentation_title="Existing Title")
        merged = self.flow._merge_gathered_info(order_form)
        
        # Existing non-empty title should be preserved
        assert merged.presentation_title == "Existing Title"


# Run with: pytest tests/test_clarifier_memory.py -v
