"""
Layout Selector Service

Selects layouts with intentional variety to avoid monotonous presentations.

Key Features:
- Weighted random selection within compatible layouts
- "No repeat" rule: Avoids using same layout consecutively
- Content-aware: Picks layouts compatible with slide content
- User preferences: Respects user-locked layouts
"""

import random
from typing import Optional, List, Dict, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.layout_models import LayoutPreset
from app.models.schemas import RefinedSlide, SlideContentType
from app.core.logging import get_logger

logger = get_logger(__name__)


# Default layout presets (used when database is empty)
DEFAULT_LAYOUTS: List[Dict[str, Any]] = [
    {
        "preset_id": "two_col_50_50",
        "name": "50/50 Two Column",
        "category": "two_column",
        "content_types": ["content", "image", "diagram", "equation"],
        "variety_group": "two_column",
        "variety_weight": 1.0,
        "regions": {"text": "left", "visual": "right", "visual_size": "50%"},
    },
    {
        "preset_id": "two_col_60_40",
        "name": "60/40 Two Column",
        "category": "two_column",
        "content_types": ["content", "image"],
        "variety_group": "two_column",
        "variety_weight": 1.0,
        "regions": {"text": "left", "visual": "right", "visual_size": "40%"},
    },
    {
        "preset_id": "two_col_40_60",
        "name": "40/60 Two Column",
        "category": "two_column",
        "content_types": ["image", "diagram"],
        "variety_group": "two_column",
        "variety_weight": 0.8,
        "regions": {"text": "left", "visual": "right", "visual_size": "60%"},
    },
    {
        "preset_id": "stacked",
        "name": "Stacked Content",
        "category": "stacked",
        "content_types": ["content", "equation"],
        "variety_group": "single_column",
        "variety_weight": 1.0,
        "regions": {"text": "top", "visual": "bottom", "visual_size": "40%"},
    },
    {
        "preset_id": "full_bleed_image",
        "name": "Full Bleed Image",
        "category": "full_width",
        "content_types": ["image"],
        "variety_group": "visual_focus",
        "variety_weight": 0.6,
        "regions": {"visual": "full", "visual_size": "100%"},
    },
    {
        "preset_id": "centered_visual",
        "name": "Centered Visual",
        "category": "centered",
        "content_types": ["diagram", "equation"],
        "variety_group": "visual_focus",
        "variety_weight": 1.0,
        "regions": {"text": "top", "visual": "center", "visual_size": "60%"},
    },
    {
        "preset_id": "text_only",
        "name": "Text Only",
        "category": "text",
        "content_types": ["content", "quote"],
        "variety_group": "text_focus",
        "variety_weight": 1.0,
        "regions": {"text": "full"},
    },
]


class LayoutSelector:
    """
    Selects layouts with intentional variety to avoid monotonous presentations.
    
    The selector uses a combination of:
    1. Content-type compatibility (only offer layouts that work for this content)
    2. Weighted random selection (some layouts are preferred over others)
    3. No-repeat rule (don't use the same layout on consecutive slides)
    4. User preference (if user explicitly chose a layout, respect it)
    """
    
    def __init__(self):
        self._in_memory_cache: Optional[List[Dict[str, Any]]] = None
    
    async def select_for_slide(
        self,
        slide: RefinedSlide,
        previous_layout_id: Optional[str] = None,
        user_preference: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        Select the best layout for this slide.
        
        Args:
            slide: The refined slide to select a layout for
            previous_layout_id: The layout used on the previous slide (to avoid repetition)
            user_preference: User's explicitly chosen layout (takes priority)
            db_session: Database session for fetching layouts
            
        Returns:
            Layout preset dict with preset_id, regions, etc.
        """
        # 1. If user explicitly chose a layout, use it
        if user_preference:
            layout = await self._get_preset(user_preference, db_session)
            if layout:
                logger.debug(f"Using user-preferred layout: {user_preference}")
                return layout
        
        # 2. Get compatible layouts for this content type
        compatible = await self._get_compatible_layouts(
            slide.content_type.value if isinstance(slide.content_type, SlideContentType) else slide.content_type,
            db_session
        )
        
        if not compatible:
            logger.warning(f"No compatible layouts found for {slide.content_type}, using default")
            compatible = [DEFAULT_LAYOUTS[0]]
        
        # 3. Apply variety rule: filter out previous layout to avoid repetition
        if previous_layout_id and len(compatible) > 1:
            compatible = [l for l in compatible if l["preset_id"] != previous_layout_id]
        
        # 4. Weighted random selection
        selected = self._weighted_choice(compatible)
        logger.debug(f"Selected layout '{selected['preset_id']}' for slide {slide.order}")
        
        return selected
    
    async def select_for_presentation(
        self,
        slides: List[RefinedSlide],
        user_preferences: Optional[Dict[int, str]] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> Dict[int, Dict[str, Any]]:
        """
        Select layouts for all slides in a presentation with variety.
        
        Args:
            slides: List of slides to assign layouts to
            user_preferences: Dict mapping slide.order to preset_id for user-locked layouts
            db_session: Database session
            
        Returns:
            Dict mapping slide.order to selected layout
        """
        user_preferences = user_preferences or {}
        result: Dict[int, Dict[str, Any]] = {}
        previous_layout_id: Optional[str] = None
        
        for slide in sorted(slides, key=lambda s: s.order):
            user_pref = user_preferences.get(slide.order)
            layout = await self.select_for_slide(
                slide=slide,
                previous_layout_id=previous_layout_id,
                user_preference=user_pref,
                db_session=db_session,
            )
            result[slide.order] = layout
            previous_layout_id = layout["preset_id"]
        
        # Log variety metrics
        unique_layouts = len(set(l["preset_id"] for l in result.values()))
        logger.info(f"[LAYOUT] Assigned {unique_layouts} unique layouts across {len(slides)} slides")
        
        return result
    
    async def _get_preset(
        self,
        preset_id: str,
        db_session: Optional[AsyncSession],
    ) -> Optional[Dict[str, Any]]:
        """Get a specific layout preset by ID."""
        # Try database first
        if db_session:
            query = select(LayoutPreset).where(
                LayoutPreset.preset_id == preset_id,
                LayoutPreset.is_active == True
            )
            result = await db_session.execute(query)
            preset = result.scalar_one_or_none()
            if preset:
                return self._preset_to_dict(preset)
        
        # Fall back to defaults
        for layout in DEFAULT_LAYOUTS:
            if layout["preset_id"] == preset_id:
                return layout
        
        return None
    
    async def _get_compatible_layouts(
        self,
        content_type: str,
        db_session: Optional[AsyncSession],
    ) -> List[Dict[str, Any]]:
        """Get all layouts compatible with this content type."""
        compatible = []
        
        # Try database first
        if db_session:
            query = select(LayoutPreset).where(LayoutPreset.is_active == True)
            result = await db_session.execute(query)
            db_presets = result.scalars().all()
            
            for preset in db_presets:
                if preset.content_types and content_type in preset.content_types:
                    compatible.append(self._preset_to_dict(preset))
        
        # If no DB layouts, use defaults
        if not compatible:
            for layout in DEFAULT_LAYOUTS:
                if content_type in layout.get("content_types", []):
                    compatible.append(layout)
        
        # If still nothing, return all defaults as fallback
        if not compatible:
            compatible = DEFAULT_LAYOUTS.copy()
        
        return compatible
    
    def _weighted_choice(self, layouts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Select a layout using weighted random selection.
        Higher variety_weight = more likely to be chosen.
        """
        if not layouts:
            return DEFAULT_LAYOUTS[0]
        
        if len(layouts) == 1:
            return layouts[0]
        
        weights = [l.get("variety_weight", 1.0) for l in layouts]
        total_weight = sum(weights)
        
        if total_weight == 0:
            return random.choice(layouts)
        
        r = random.uniform(0, total_weight)
        cumulative = 0.0
        
        for layout, weight in zip(layouts, weights):
            cumulative += weight
            if r <= cumulative:
                return layout
        
        return layouts[-1]
    
    def _preset_to_dict(self, preset: LayoutPreset) -> Dict[str, Any]:
        """Convert a LayoutPreset model to a dict."""
        return {
            "id": str(preset.id),
            "preset_id": preset.preset_id,
            "name": preset.name,
            "description": preset.description,
            "category": preset.category,
            "content_types": preset.content_types or [],
            "variety_group": preset.variety_group,
            "variety_weight": preset.variety_weight or 1.0,
            "regions": preset.regions or {},
            "css_grid": preset.css_grid,
            "thumbnail_url": preset.thumbnail_url,
        }


# Singleton instance
_layout_selector: Optional[LayoutSelector] = None


def get_layout_selector() -> LayoutSelector:
    """Get the singleton LayoutSelector instance."""
    global _layout_selector
    if _layout_selector is None:
        _layout_selector = LayoutSelector()
    return _layout_selector
