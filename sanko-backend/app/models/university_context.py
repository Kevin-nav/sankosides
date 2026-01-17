"""
University Context Schema.

This module provides the UniversityContext class that encapsulates
all university-specific information needed by agents. It provides:

1. Defaults for OrderForm fields based on university rules
2. Prompt injection text for agent system prompts
3. Compliance rules for the Refiner agent
4. Helper methods for accessing university/department metadata
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.core.university_configs.base import (
    UniversityConfig,
    FacultyConfig,
    DepartmentConfig,
    FormattingRules,
)
from app.core.university_configs.registry import UniversityRegistry


class UniversityContext(BaseModel):
    """
    Context injected into all agents for institution-specific decisions.
    
    This class bridges the user's profile data with the agent pipeline,
    providing formatted prompts and defaults based on their institution.
    
    Usage:
        # Build from user profile data
        context = UniversityContext.from_user_profile(
            university_id="umat",
            faculty_id="fmmt",
            department_id="mining_engineering",
            academic_level="undergraduate",
        )
        
        # Get defaults for OrderForm
        defaults = context.get_clarifier_defaults()
        
        # Get prompt injection for agents
        prompt = context.get_agent_prompt_injection()
    """
    
    # Core university config
    university: UniversityConfig
    faculty: Optional[FacultyConfig] = None
    department: Optional[DepartmentConfig] = None
    
    # User academic context
    academic_level: str = Field(
        default="undergraduate",
        description="User's academic level: undergraduate, masters, phd, faculty"
    )
    academic_year: Optional[int] = Field(
        default=None,
        description="Academic year (1-4 for undergrads)"
    )
    programme_name: Optional[str] = Field(
        default=None,
        description="Specific BSc programme name"
    )
    
    # Presentation context (from current project)
    presentation_type: Optional[str] = Field(
        default=None,
        description="Type: thesis_defense, class_assignment, seminar, conference"
    )
    
    class Config:
        arbitrary_types_allowed = True
    
    # =========================================================================
    # FACTORY METHODS
    # =========================================================================
    
    @classmethod
    def from_user_profile(
        cls,
        university_id: str,
        faculty_id: Optional[str] = None,
        department_id: Optional[str] = None,
        academic_level: str = "undergraduate",
        academic_year: Optional[int] = None,
        programme_name: Optional[str] = None,
        presentation_type: Optional[str] = None,
    ) -> Optional["UniversityContext"]:
        """
        Build UniversityContext from user profile fields.
        
        Returns None if university is not supported.
        """
        university = UniversityRegistry.get(university_id)
        if not university:
            return None
        
        faculty = None
        department = None
        
        if faculty_id:
            faculty = university.get_faculty(faculty_id)
            if faculty and department_id:
                department = faculty.get_department(department_id)
        elif department_id:
            # Find department across all faculties
            department = university.find_department_by_id(department_id)
            if department:
                faculty = university.get_faculty_for_department(department_id)
        
        return cls(
            university=university,
            faculty=faculty,
            department=department,
            academic_level=academic_level,
            academic_year=academic_year,
            programme_name=programme_name,
            presentation_type=presentation_type,
        )
    
    # =========================================================================
    # CLARIFIER AGENT SUPPORT
    # =========================================================================
    
    def get_clarifier_defaults(self) -> Dict[str, Any]:
        """
        Get default OrderForm values based on university.
        
        These defaults are applied by the Clarifier agent so it
        doesn't need to ask the user for institution-known settings.
        """
        defaults = {
            "citation_style": self.university.default_citation_style,
            "references_placement": self.university.formatting_rules.reference_placement,
            "tone": "academic",
        }
        
        # Add thesis-specific defaults for defense presentations
        if self.presentation_type == "thesis_defense":
            defaults["emphasis_style"] = "detailed"
            defaults["target_slides"] = 15  # Typical thesis defense length
        
        return defaults
    
    # =========================================================================
    # AGENT PROMPT INJECTION
    # =========================================================================
    
    def get_agent_prompt_injection(self) -> str:
        """
        Generate prompt text to inject into agent system prompts.
        
        This provides the agent with all university-specific rules
        in a format optimized for LLM comprehension.
        """
        rules = self.university.formatting_rules
        
        prompt = f"""
## UNIVERSITY-SPECIFIC REQUIREMENTS (CRITICAL - MUST FOLLOW)

**Institution:** {self.university.name} ({self.university.short_name})
**Country:** {self.university.country}
"""
        
        # Add faculty/department context if available
        if self.faculty:
            prompt += f"**Faculty:** {self.faculty.name} ({self.faculty.short_name})\n"
        if self.department:
            prompt += f"**Department:** {self.department.name}\n"
        if self.programme_name:
            prompt += f"**Programme:** {self.programme_name}\n"
        
        # Academic standards section
        prompt += f"""
### Academic Standards (MANDATORY)
- **Citation Style:** {self.university.default_citation_style.upper()} System
  - Single author: (Surname, Year) e.g., (Cobblah, 1997)
  - Two authors: (Surname and Surname, Year) e.g., (Mireku-Gyimah and Suglo, 1993)
  - 3+ authors: (First Author et al., Year) e.g., (Temeng et al., 2000)
- **Spelling:** {self.university.spelling_variant.title()} English (e.g., "colour" not "color", "organisation" not "organization")
- **Units:** {self.university.unit_system.upper()} Units with {'space' if rules.number_unit_spacing else 'no space'} between number and unit
  - Correct: "80 cm", "50 kg", "20 °C"
  - Incorrect: "80cm", "50kg", "20°C"

### Formatting Rules (MANDATORY)
- **Figure captions:** Place {rules.figure_caption_position.upper()} the figure
- **Table captions:** Place {rules.table_caption_position.upper()} the table
- **References:** On {rules.reference_placement.replace('_', ' ')}, alphabetically ordered
- **Acronyms:** {rules.acronym_first_use.replace('_', ' ').title()} on first use
  - Example: "University of Mines and Technology (UMaT)" then "UMaT" thereafter
"""
        
        return prompt
    
    def get_planner_context(self) -> str:
        """
        Get additional context specifically for the Planner agent.
        
        Includes STEM-specific diagram and equation suggestions
        based on the user's department.
        """
        base_prompt = self.get_agent_prompt_injection()
        
        if not self.department:
            return base_prompt
        
        # Add department-specific suggestions
        dept = self.department
        
        planner_additions = """
### Department-Specific Suggestions

"""
        
        if dept.common_diagram_types:
            diagram_types = ", ".join(dept.common_diagram_types[:5])
            planner_additions += f"**Common Diagrams for {dept.name}:** {diagram_types}\n"
        
        if dept.common_equation_domains:
            equation_domains = ", ".join(dept.common_equation_domains[:5])
            planner_additions += f"**Common Equation Domains:** {equation_domains}\n"
        
        if dept.preferred_journals:
            journals = ", ".join(dept.preferred_journals[:3])
            planner_additions += f"**Preferred Journals:** {journals}\n"
        
        return base_prompt + planner_additions
    
    def get_refiner_compliance_context(self) -> str:
        """
        Get compliance checking context for the Refiner agent.
        
        Provides a checklist of rules to verify before output.
        """
        rules = self.university.formatting_rules
        
        return f"""
## COMPLIANCE VERIFICATION CHECKLIST ({self.university.short_name})

Before finalizing output, verify ALL slides comply with these standards:

### Citation Compliance
- [ ] All citations use {self.university.default_citation_style.upper()} format
- [ ] In-text citations follow pattern: (Author, Year)
- [ ] Multiple authors use "and" (not "&")
- [ ] 3+ authors use "et al."

### Language Compliance  
- [ ] All text uses {self.university.spelling_variant.title()} English spelling
- [ ] Common words checked: colour/color, organisation/organization, behaviour/behavior

### Unit Compliance
- [ ] All measurements use SI units
- [ ] Space between number and unit: "80 cm" not "80cm"
- [ ] Temperature format: "20 °C" (space before °, no space between ° and C)
- [ ] No periods after unit abbreviations: "kg" not "kg."

### Visual Compliance
- [ ] Figure captions are {rules.figure_caption_position.upper()} figures
- [ ] Table captions are {rules.table_caption_position.upper()} tables
- [ ] Acronyms spelled out on first use

### Reference Compliance
- [ ] References appear on {rules.reference_placement.replace('_', ' ')}
- [ ] References are alphabetically ordered by author surname

If ANY rule is violated, FIX IT before output. Do not ask for permission to fix compliance issues.
"""
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def get_citation_style(self) -> str:
        """Get the applicable citation style."""
        # Check for department override first
        if self.department and self.department.citation_style_override:
            return self.department.citation_style_override
        return self.university.default_citation_style
    
    def is_stem_department(self) -> bool:
        """Check if the user is in a STEM department."""
        if self.department:
            return self.department.is_stem
        return True  # Default to STEM for UMaT
    
    def get_diagram_suggestions(self) -> List[str]:
        """Get suggested diagram types for this department."""
        if self.department:
            return self.department.common_diagram_types
        return []
    
    def get_equation_domains(self) -> List[str]:
        """Get common equation domains for this department."""
        if self.department:
            return self.department.common_equation_domains
        return []
    
    def get_preferred_journals(self) -> List[str]:
        """Get preferred journals for citation search."""
        if self.department:
            return self.department.preferred_journals
        return []
    
    def get_branding_colors(self) -> Dict[str, str]:
        """Get university branding colors for templates."""
        return {
            "primary": self.university.primary_color,
            "secondary": self.university.secondary_color,
        }


# =============================================================================
# HELPER FUNCTION FOR BUILDING CONTEXT FROM DB USER
# =============================================================================

async def get_university_context_for_user(
    user_id: str,
    session: Any,  # AsyncSession - typed loosely to avoid circular imports
    presentation_type: Optional[str] = None,
) -> Optional[UniversityContext]:
    """
    Build UniversityContext from a user's database record.
    
    This is the main entry point for getting context to inject into agents.
    
    Args:
        user_id: The user's UUID
        session: SQLAlchemy async session
        presentation_type: Optional presentation context
        
    Returns:
        UniversityContext if user has a supported university, None otherwise
    """
    from sqlalchemy import text
    
    # Get user's university profile from database
    query = """
        SELECT 
            university_id, faculty_id, department_id,
            academic_level, academic_year, programme_id
        FROM users 
        WHERE id = :user_id
    """
    
    result = await session.execute(text(query), {"user_id": user_id})
    user = result.fetchone()
    
    if not user or not user.university_id:
        return None
    
    # Load full university config from registry
    university_config = await UniversityRegistry.get(user.university_id, session)
    
    if not university_config:
        return None
    
    return UniversityContext.from_user_profile(
        university_id=user.university_id,
        faculty_id=user.faculty_id,
        department_id=user.department_id,
        academic_level=user.academic_level or "undergraduate",
        academic_year=user.academic_year,
        programme_name=user.programme_id,
        presentation_type=presentation_type,
    )
