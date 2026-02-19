"""Structured slide element tree models."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class ElementType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    EQUATION = "equation"
    DIAGRAM = "diagram"
    SHAPE = "shape"
    CHART = "chart"


class TextRun(BaseModel):
    text: str
    bold: bool = False
    italic: bool = False
    size: Optional[int] = None
    color: Optional[str] = None
    font: Optional[str] = None


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    runs: List[TextRun] = Field(default_factory=list)


class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    url: str
    alt: Optional[str] = None
    caption: Optional[str] = None
    citation: Optional[str] = None
    crop: Optional[Dict[str, float]] = None


class EquationContent(BaseModel):
    type: Literal["equation"] = "equation"
    latex: str
    rendered_svg: Optional[str] = None


class DiagramContent(BaseModel):
    type: Literal["diagram"] = "diagram"
    mermaid_source: Optional[str] = None
    rendered_svg: Optional[str] = None


class ShapeContent(BaseModel):
    type: Literal["shape"] = "shape"
    shape: Literal["rectangle", "circle", "line", "arrow"] = "rectangle"
    label: Optional[str] = None


class ChartContent(BaseModel):
    type: Literal["chart"] = "chart"
    chart_config: Dict[str, object] = Field(default_factory=dict)


ElementContent = Annotated[
    Union[
        TextContent,
        ImageContent,
        EquationContent,
        DiagramContent,
        ShapeContent,
        ChartContent,
    ],
    Field(discriminator="type"),
]


class BackgroundConfig(BaseModel):
    type: Literal["solid", "gradient", "image"] = "solid"
    color: Optional[str] = "#FFFFFF"
    gradient: Optional[str] = None
    image_url: Optional[str] = None


class ElementStyle(BaseModel):
    color: Optional[str] = None
    background: Optional[str] = None
    border: Optional[str] = None
    border_radius: Optional[float] = None
    opacity: Optional[float] = None
    shadow: Optional[str] = None


class LayoutConstraint(BaseModel):
    type: str
    elements: List[str] = Field(default_factory=list)
    metadata: Dict[str, object] = Field(default_factory=dict)


class SlideElement(BaseModel):
    id: str
    type: ElementType
    x: float
    y: float
    width: float
    height: float
    z_index: int = 0
    rotation: float = 0.0
    locked: bool = False
    style: ElementStyle = Field(default_factory=ElementStyle)
    content: ElementContent

    @field_validator("x", "y", "width", "height")
    @classmethod
    def _percent_in_bounds(cls, value: float) -> float:
        if value < 0 or value > 100:
            raise ValueError("percentage values must be in [0, 100]")
        return value

    @field_validator("rotation")
    @classmethod
    def _rotation_bounds(cls, value: float) -> float:
        if value < 0 or value > 360:
            raise ValueError("rotation must be in [0, 360]")
        return value

    @model_validator(mode="after")
    def _validate_geometry_and_type(self):
        if self.width <= 0 or self.height <= 0:
            raise ValueError("width and height must be positive")
        if self.x + self.width > 100 or self.y + self.height > 100:
            raise ValueError("element bounds exceed slide dimensions")
        if self.type.value != self.content.type:
            raise ValueError("element type must match content type")
        return self


class SlideElementTree(BaseModel):
    slide_id: str
    order: int = Field(..., ge=1)
    layout_id: str
    background: BackgroundConfig = Field(default_factory=BackgroundConfig)
    elements: List[SlideElement] = Field(default_factory=list)
    constraints: List[LayoutConstraint] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
