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
import asyncio
from typing import Optional, List, Dict, Any

from app.models.schemas import RefinedSlide, SlideContentType
from app.core.logging import get_logger
from app.core.convex_client import get_convex_client
from app.services.unified_cache import layout_cache

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
        self.convex_client = get_convex_client()

    async def _get_active_layouts_cached(self) -> List[Dict[str, Any]]:
        """
        Fetch active layouts with shared cache to avoid repeated Convex calls.
        """
        cached = layout_cache.get("active")
        if cached is not None:
            return cached

        active_layouts = await asyncio.to_thread(
            self.convex_client.query,
            "layoutPresets:getActive",
            {},
        )
        layout_cache.set("active", active_layouts)
        return active_layouts
    
    async def select_for_slide(
        self,
        slide: RefinedSlide,
        previous_layout_id: Optional[str] = None,
        user_preference: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Select the best layout for this slide.
        
        Args:
            slide: The refined slide to select a layout for
            previous_layout_id: The layout used on the previous slide (to avoid repetition)
            user_preference: User's explicitly chosen layout (takes priority)
            
        Returns:
            Layout preset dict with preset_id, regions, etc.
        """
        # 1. If user explicitly chose a layout, use it
        if user_preference:
            layout = await self._get_preset(user_preference)
            if layout:
                logger.debug(f"Using user-preferred layout: {user_preference}")
                return layout
        
        # 2. Get compatible layouts for this content type
        compatible = await self._get_compatible_layouts(
            slide.content_type.value if isinstance(slide.content_type, SlideContentType) else slide.content_type
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
    ) -> Dict[int, Dict[str, Any]]:
        """
        Select layouts for all slides in a presentation with variety.
        
        Args:
            slides: List of slides to assign layouts to
            user_preferences: Dict mapping slide.order to preset_id for user-locked layouts
            
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
    ) -> Optional[Dict[str, Any]]:
        """Get a specific layout preset by ID."""
        cache_key = f"preset:{preset_id}"
        cached = layout_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            # Check active presets first to avoid an extra remote call.
            active_layouts = await self._get_active_layouts_cached()
            for preset in active_layouts:
                if preset.get("presetId") == preset_id:
                    normalized = self._convex_to_dict(preset)
                    layout_cache.set(cache_key, normalized)
                    return normalized

            # Fetch from Convex by ID as fallback
            dataset = self.convex_client.query("layoutPresets:getById", {"presetId": preset_id})
            
            if dataset:
                normalized = self._convex_to_dict(dataset)
                layout_cache.set(cache_key, normalized)
                return normalized
        except Exception as e:
            logger.error(f"Failed to fetch layout preset from Convex: {e}")
            
        # Fall back to defaults
        for layout in DEFAULT_LAYOUTS:
            if layout["preset_id"] == preset_id:
                return layout
        
        return None
    
    async def _get_compatible_layouts(
        self,
        content_type: str,
    ) -> List[Dict[str, Any]]:
        """Get all layouts compatible with this content type."""
        compatible = []
        
        try:
            # Fetch all active layouts from shared cache/Convex
            active_layouts = await self._get_active_layouts_cached()
            
            for preset in active_layouts:
                config = preset.get("config", {})
                cts = config.get("content_types", [])
                if cts and content_type in cts:
                    compatible.append(self._convex_to_dict(preset))
                    
        except Exception as e:
            logger.error(f"Failed to fetch layouts from Convex: {e}")
        
        # If no DB layouts or error, use defaults
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
    
    def _convex_to_dict(self, preset: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a Convex layout preset to the internal dict format."""
        config = preset.get("config", {})
        return {
            "id": preset.get("_id"),
            "preset_id": preset.get("presetId"),
            "name": preset.get("name"),
            "description": preset.get("description"),
            "category": config.get("category"),
            "content_types": config.get("content_types", []),
            "variety_group": config.get("variety_group"),
            "variety_weight": config.get("variety_weight", 1.0),
            "regions": config.get("regions", {}),
            "css_grid": config.get("css_grid"),
            "thumbnail_url": config.get("thumbnail_url"),
        }


# Singleton instance
_layout_selector: Optional[LayoutSelector] = None


def get_layout_selector() -> LayoutSelector:
    """Get the singleton LayoutSelector instance."""
    global _layout_selector
    if _layout_selector is None:
        _layout_selector = LayoutSelector()
    return _layout_selector
