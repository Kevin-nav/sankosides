"""
Base schemas for University Configuration System.

These Pydantic models define the structure for university-specific
configurations that drive agent steering, compliance checking, and
template customization.
"""

from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ThankYouConfig(BaseModel):
    """Configuration for Thank You slide elements."""
    show_logo: bool = Field(default=True, description="Show university logo")
    show_presenter_name: bool = Field(default=False, description="Show presenter name if provided")
    custom_message: Optional[str] = Field(default=None, description="Custom message instead of 'Thank You'")


class ReferenceConfig(BaseModel):
    """
    Configuration for citation and reference behavior.
    Each university can have custom rules.
    """
    # Inline citation format
    inline_format: Literal["author_year", "numbered"] = Field(
        default="author_year",
        description="Format for inline citations: (Smith, 2024) or [1]"
    )
    
    # Multiple citations per statement
    allow_multiple_citations: bool = Field(
        default=True,
        description="Allow (Smith, 2024; Jones, 2023) format"
    )
    
    # Reference list ordering
    ordering: Literal["alphabetical", "appearance"] = Field(
        default="alphabetical",
        description="How to order references on References slide"
    )
    
    # Reference list numbering
    use_numbered_list: bool = Field(
        default=False,
        description="Use numbered list (for IEEE) vs bullets (for Harvard/APA)"
    )
    
    @classmethod
    def from_citation_style(cls, style: str) -> "ReferenceConfig":
        """Create config based on citation style."""
        if style.lower() == "ieee":
            return cls(
                inline_format="numbered",
                ordering="appearance",
                use_numbered_list=True,
            )
        else:  # harvard, apa, chicago
            return cls(
                inline_format="author_year",
                ordering="alphabetical",
                use_numbered_list=False,
            )



class ImageConfig(BaseModel):
    """Configuration for image captions and attributions."""
    
    # Caption format
    caption_format: str = Field(
        default="Figure {n}: {caption}",
        description="Template for image captions. {n}=number, {caption}=description"
    )
    
    # Source attribution format
    source_format: str = Field(
        default="Source: {source}",
        description="Template for source attribution. {source}=citation or URL"
    )
    
    # Where to show attribution
    attribution_position: Literal["below_caption", "slide_footer"] = Field(
        default="below_caption",
        description="Where to display source attribution"
    )
    
    # Include images in References slide
    include_in_references: bool = Field(
        default=True,
        description="Whether to include image sources in References slide"
    )
    
    # Numbering style
    numbering_prefix: str = Field(
        default="Figure",
        description="Prefix for figure numbering (Figure, Fig., Diagram, etc.)"
    )


class FormattingRules(BaseModel):
    """
    Formatting rules for an institution.
    
    These rules are injected into agent prompts to ensure
    generated content complies with institutional standards.
    """
    # Caption placement
    figure_caption_position: Literal["above", "below"] = Field(
        default="below",
        description="Where figure titles/captions should be placed"
    )
    table_caption_position: Literal["above", "below"] = Field(
        default="above", 
        description="Where table titles/captions should be placed"
    )
    
    # Reference handling
    reference_placement: Literal["distributed", "last_slide"] = Field(
        default="last_slide",
        description="Where to place citation references in the presentation"
    )
    
    # Text formatting
    acronym_first_use: Literal["spell_out", "abbreviate"] = Field(
        default="spell_out",
        description="How to handle acronyms on first use"
    )
    number_unit_spacing: bool = Field(
        default=True,
        description="Whether to include space between number and unit (e.g., '80 cm' vs '80cm')"
    )
    
    # Thank You slide configuration
    thank_you: ThankYouConfig = Field(
        default_factory=ThankYouConfig,
        description="Configuration for Thank You slide"
    )
    
    # Reference configuration
    references: ReferenceConfig = Field(
        default_factory=ReferenceConfig,
        description="Configuration for citations and references"
    )
    
    # Image configuration
    images: ImageConfig = Field(
        default_factory=ImageConfig,
        description="Configuration for image captions and attributions"
    )


class DepartmentConfig(BaseModel):
    """
    Department-specific configuration within a faculty.
    
    Includes STEM-specific metadata for agent steering:
    - Common diagram types for the Planner to suggest
    - Common equation domains for LaTeX generation
    - Preferred journals for citation search
    """
    department_id: str = Field(..., description="Unique identifier (e.g., 'mining_engineering')")
    name: str = Field(..., description="Display name (e.g., 'Mining Engineering')")
    
    # Programmes offered (BSc only for MVP)
    bsc_programmes: List[str] = Field(
        default_factory=list,
        description="List of BSc programme names offered by this department"
    )
    
    # STEM classification
    is_stem: bool = Field(
        default=True,
        description="Whether this is a STEM department"
    )
    
    # Agent steering metadata for Planner/Outliner
    common_diagram_types: List[str] = Field(
        default_factory=list,
        description="Common diagram types for this department (e.g., 'flowchart', 'geological_cross_section')"
    )
    common_equation_domains: List[str] = Field(
        default_factory=list,
        description="Common equation domains for LaTeX generation (e.g., 'thermodynamics', 'rock_mechanics')"
    )
    
    # Citation preferences for Refiner
    preferred_journals: List[str] = Field(
        default_factory=list,
        description="Preferred academic journals for this department"
    )
    
    # Optional overrides
    citation_style_override: Optional[str] = Field(
        default=None,
        description="Override citation style for this department (if different from university default)"
    )


class FacultyConfig(BaseModel):
    """
    Faculty configuration containing multiple departments.
    
    Represents a major academic division within the university
    (e.g., Faculty of Engineering, School of Petroleum Studies).
    """
    faculty_id: str = Field(..., description="Unique identifier (e.g., 'foe', 'spets')")
    name: str = Field(..., description="Full name (e.g., 'Faculty of Engineering')")
    short_name: str = Field(..., description="Short name/abbreviation (e.g., 'FoE')")
    
    # Departments within this faculty
    departments: Dict[str, DepartmentConfig] = Field(
        default_factory=dict,
        description="Department configurations keyed by department_id"
    )
    
    def get_department(self, department_id: str) -> Optional[DepartmentConfig]:
        """Get a department by ID."""
        return self.departments.get(department_id)
    
    def get_all_programmes(self) -> List[str]:
        """Get all BSc programmes across all departments."""
        programmes = []
        for dept in self.departments.values():
            programmes.extend(dept.bsc_programmes)
        return programmes


class UniversityConfig(BaseModel):
    """
    Complete configuration for a supported university.
    
    This is the top-level configuration that contains all institution-specific
    rules, branding, and academic structure. It is used to:
    
    1. Inject context into agent prompts (Clarifier, Planner, Refiner)
    2. Set defaults for OrderForm fields
    3. Drive compliance checking rules
    4. Apply university branding to templates
    """
    # Identity
    university_id: str = Field(..., description="Unique identifier (e.g., 'umat')")
    name: str = Field(..., description="Full name (e.g., 'University of Mines and Technology')")
    short_name: str = Field(..., description="Short name (e.g., 'UMaT')")
    country: str = Field(..., description="Country (e.g., 'Ghana')")
    
    # Academic Standards
    default_citation_style: Literal["harvard", "apa", "ieee", "chicago"] = Field(
        ...,
        description="Default citation style for this institution"
    )
    spelling_variant: Literal["british", "american"] = Field(
        ...,
        description="English spelling variant required"
    )
    unit_system: Literal["si", "imperial"] = Field(
        default="si",
        description="Unit system required"
    )
    
    # Visual/Branding
    primary_color: str = Field(
        default="#1E3A5F",
        description="Primary brand color (hex)"
    )
    secondary_color: str = Field(
        default="#D4AF37",
        description="Secondary/accent color (hex)"
    )
    logo_url: Optional[str] = Field(
        default=None,
        description="URL to university logo"
    )
    
    # Formatting Rules
    formatting_rules: FormattingRules = Field(
        default_factory=FormattingRules,
        description="Institution-specific formatting rules"
    )
    
    # Academic Structure
    faculties: Dict[str, FacultyConfig] = Field(
        default_factory=dict,
        description="Faculty configurations keyed by faculty_id"
    )
    
    # Feature flags for phased rollout
    compliance_checking_enabled: bool = Field(
        default=False,
        description="Whether Phase 2 compliance engine is enabled for this university"
    )
    custom_templates_enabled: bool = Field(
        default=False,
        description="Whether Phase 3 custom templates are enabled"
    )
    
    # Helper methods
    def get_faculty(self, faculty_id: str) -> Optional[FacultyConfig]:
        """Get a faculty by ID."""
        return self.faculties.get(faculty_id)
    
    def get_department(self, faculty_id: str, department_id: str) -> Optional[DepartmentConfig]:
        """Get a department by faculty and department ID."""
        faculty = self.get_faculty(faculty_id)
        if faculty:
            return faculty.get_department(department_id)
        return None
    
    def find_department_by_id(self, department_id: str) -> Optional[DepartmentConfig]:
        """Find a department by ID across all faculties."""
        for faculty in self.faculties.values():
            dept = faculty.get_department(department_id)
            if dept:
                return dept
        return None
    
    def get_all_programmes(self) -> List[str]:
        """Get all BSc programmes across all faculties."""
        programmes = []
        for faculty in self.faculties.values():
            programmes.extend(faculty.get_all_programmes())
        return programmes
    
    def get_faculty_for_department(self, department_id: str) -> Optional[FacultyConfig]:
        """Find which faculty a department belongs to."""
        for faculty in self.faculties.values():
            if department_id in faculty.departments:
                return faculty
        return None


class UniversitySummary(BaseModel):
    """
    Lightweight summary of a university for listing purposes.
    
    Used by the frontend to populate dropdowns without loading
    full configuration data.
    """
    university_id: str
    name: str
    short_name: str
    country: str
    faculty_count: int
    department_count: int
    programme_count: int
