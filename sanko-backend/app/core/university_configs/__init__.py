"""
University Configuration System

This module provides the configuration infrastructure for university-specific
agent steering and compliance rules. Configurations are stored in the database
and loaded dynamically via the UniversityRegistry.

Database tables (see alembic migrations):
- universities: Core institution data and formatting rules
- faculties: Academic divisions within universities  
- departments: Departments within faculties with STEM metadata
- programmes: Degree programmes offered by departments

Usage:
    from app.core.university_configs import UniversityRegistry
    
    # Get a university config
    config = await UniversityRegistry.get("umat", session)
    
    # List supported universities
    universities = await UniversityRegistry.get_all_supported(session)
"""

from app.core.university_configs.base import (
    UniversityConfig,
    FacultyConfig,
    DepartmentConfig,
    FormattingRules,
    UniversitySummary,
)
from app.core.university_configs.registry import UniversityRegistry

__all__ = [
    "UniversityConfig",
    "FacultyConfig", 
    "DepartmentConfig",
    "FormattingRules",
    "UniversitySummary",
    "UniversityRegistry",
]
