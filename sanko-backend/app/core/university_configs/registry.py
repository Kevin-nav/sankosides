"""
University Registry - Database-Driven Implementation.

This service provides access to university configurations stored in the database.
It replaces the hardcoded Python configuration approach with dynamic database queries.

Usage:
    # Get a university
    config = await UniversityRegistry.get("umat", session)
    
    # List all supported universities
    universities = await UniversityRegistry.get_all_supported(session)
    
    # Check if supported
    is_supported = await UniversityRegistry.is_supported("umat", session)
"""

from typing import List, Optional, Any
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.university_configs.base import (
    UniversityConfig,
    FacultyConfig,
    DepartmentConfig,
    FormattingRules,
    UniversitySummary,
)


class UniversityRegistry:
    """
    Database-driven registry for university configurations.
    
    This class provides async methods to query university data from the database
    and convert it to Pydantic models for use in the application.
    """
    
    @classmethod
    async def get(
        cls, 
        university_id: str, 
        session: AsyncSession,
        include_inactive: bool = False
    ) -> Optional[UniversityConfig]:
        """
        Get a university configuration by ID.
        
        Args:
            university_id: The university identifier (e.g., 'umat')
            session: Database session
            include_inactive: Whether to include inactive universities
            
        Returns:
            UniversityConfig if found, None otherwise
        """
        from sqlalchemy import text
        
        # Query university with all related data
        query = """
            SELECT 
                u.id, u.university_id, u.name, u.short_name, u.country,
                u.default_citation_style, u.spelling_variant, u.unit_system,
                u.primary_color, u.secondary_color, u.logo_url,
                u.formatting_rules, u.compliance_checking_enabled, 
                u.custom_templates_enabled, u.is_active
            FROM universities u
            WHERE u.university_id = :university_id
        """
        
        if not include_inactive:
            query += " AND u.is_active = true"
        
        result = await session.execute(text(query), {"university_id": university_id})
        row = result.fetchone()
        
        if not row:
            return None
        
        # Build UniversityConfig from database row
        formatting_rules = FormattingRules(**(row.formatting_rules or {}))
        
        # Load faculties
        faculties = await cls._load_faculties(row.id, session)
        
        return UniversityConfig(
            university_id=row.university_id,
            name=row.name,
            short_name=row.short_name,
            country=row.country,
            default_citation_style=row.default_citation_style,
            spelling_variant=row.spelling_variant,
            unit_system=row.unit_system,
            primary_color=row.primary_color,
            secondary_color=row.secondary_color,
            logo_url=row.logo_url,
            formatting_rules=formatting_rules,
            compliance_checking_enabled=row.compliance_checking_enabled,
            custom_templates_enabled=row.custom_templates_enabled,
            faculties=faculties,
        )
    
    @classmethod
    async def _load_faculties(
        cls, 
        university_uuid: UUID, 
        session: AsyncSession
    ) -> dict[str, FacultyConfig]:
        """Load all faculties for a university."""
        from sqlalchemy import text
        
        faculties_query = """
            SELECT id, faculty_id, name, short_name, display_order
            FROM faculties
            WHERE university_id = :university_id AND is_active = true
            ORDER BY display_order
        """
        
        result = await session.execute(
            text(faculties_query), 
            {"university_id": university_uuid}
        )
        
        faculties = {}
        for row in result.fetchall():
            departments = await cls._load_departments(row.id, session)
            faculties[row.faculty_id] = FacultyConfig(
                faculty_id=row.faculty_id,
                name=row.name,
                short_name=row.short_name,
                departments=departments,
            )
        
        return faculties
    
    @classmethod
    async def _load_departments(
        cls, 
        faculty_uuid: UUID, 
        session: AsyncSession
    ) -> dict[str, DepartmentConfig]:
        """Load all departments for a faculty."""
        from sqlalchemy import text
        
        departments_query = """
            SELECT 
                id, department_id, name, is_stem,
                common_diagram_types, common_equation_domains, 
                preferred_journals, citation_style_override
            FROM departments
            WHERE faculty_id = :faculty_id AND is_active = true
            ORDER BY display_order
        """
        
        result = await session.execute(
            text(departments_query), 
            {"faculty_id": faculty_uuid}
        )
        
        departments = {}
        for row in result.fetchall():
            # Load programmes for this department
            programmes = await cls._load_programmes(row.id, session)
            
            departments[row.department_id] = DepartmentConfig(
                department_id=row.department_id,
                name=row.name,
                is_stem=row.is_stem,
                bsc_programmes=programmes,
                common_diagram_types=row.common_diagram_types or [],
                common_equation_domains=row.common_equation_domains or [],
                preferred_journals=row.preferred_journals or [],
                citation_style_override=row.citation_style_override,
            )
        
        return departments
    
    @classmethod
    async def _load_programmes(
        cls, 
        department_uuid: UUID, 
        session: AsyncSession
    ) -> list[str]:
        """Load BSc programme names for a department."""
        from sqlalchemy import text
        
        programmes_query = """
            SELECT name
            FROM programmes
            WHERE department_id = :department_id 
              AND level = 'undergraduate' 
              AND is_active = true
            ORDER BY display_order
        """
        
        result = await session.execute(
            text(programmes_query), 
            {"department_id": department_uuid}
        )
        
        return [row.name for row in result.fetchall()]
    
    @classmethod
    async def get_all_supported(
        cls, 
        session: AsyncSession,
        country: Optional[str] = None
    ) -> List[UniversitySummary]:
        """
        Get list of all supported universities.
        
        Args:
            session: Database session
            country: Optional filter by country
            
        Returns:
            List of UniversitySummary objects for frontend display
        """
        from sqlalchemy import text
        
        query = """
            SELECT 
                u.university_id, u.name, u.short_name, u.country,
                COUNT(DISTINCT f.id) as faculty_count,
                COUNT(DISTINCT d.id) as department_count,
                COUNT(DISTINCT p.id) as programme_count
            FROM universities u
            LEFT JOIN faculties f ON f.university_id = u.id AND f.is_active = true
            LEFT JOIN departments d ON d.faculty_id = f.id AND d.is_active = true
            LEFT JOIN programmes p ON p.department_id = d.id AND p.is_active = true
            WHERE u.is_active = true
        """
        
        params = {}
        if country:
            query += " AND u.country = :country"
            params["country"] = country
        
        query += " GROUP BY u.id ORDER BY u.name"
        
        result = await session.execute(text(query), params)
        
        return [
            UniversitySummary(
                university_id=row.university_id,
                name=row.name,
                short_name=row.short_name,
                country=row.country,
                faculty_count=row.faculty_count,
                department_count=row.department_count,
                programme_count=row.programme_count,
            )
            for row in result.fetchall()
        ]
    
    @classmethod
    async def is_supported(
        cls, 
        university_id: str, 
        session: AsyncSession
    ) -> bool:
        """
        Check if a university is supported.
        
        Args:
            university_id: The university identifier
            session: Database session
            
        Returns:
            True if supported and active, False otherwise
        """
        from sqlalchemy import text
        
        query = """
            SELECT 1 FROM universities 
            WHERE university_id = :university_id AND is_active = true
            LIMIT 1
        """
        
        result = await session.execute(text(query), {"university_id": university_id})
        return result.fetchone() is not None
    
    @classmethod
    async def get_faculties(
        cls, 
        university_id: str, 
        session: AsyncSession
    ) -> List[dict]:
        """
        Get all faculties for a university (for frontend dropdowns).
        
        Returns lightweight dict format for API responses.
        """
        from sqlalchemy import text
        
        query = """
            SELECT f.faculty_id, f.name, f.short_name
            FROM faculties f
            JOIN universities u ON f.university_id = u.id
            WHERE u.university_id = :university_id 
              AND u.is_active = true 
              AND f.is_active = true
            ORDER BY f.display_order
        """
        
        result = await session.execute(text(query), {"university_id": university_id})
        
        return [
            {"faculty_id": row.faculty_id, "name": row.name, "short_name": row.short_name}
            for row in result.fetchall()
        ]
    
    @classmethod
    async def get_departments(
        cls, 
        university_id: str, 
        faculty_id: str, 
        session: AsyncSession
    ) -> List[dict]:
        """
        Get all departments for a faculty (for frontend dropdowns).
        
        Returns lightweight dict format for API responses.
        """
        from sqlalchemy import text
        
        query = """
            SELECT d.department_id, d.name, d.is_stem
            FROM departments d
            JOIN faculties f ON d.faculty_id = f.id
            JOIN universities u ON f.university_id = u.id
            WHERE u.university_id = :university_id 
              AND f.faculty_id = :faculty_id
              AND u.is_active = true 
              AND f.is_active = true
              AND d.is_active = true
            ORDER BY d.display_order
        """
        
        result = await session.execute(
            text(query), 
            {"university_id": university_id, "faculty_id": faculty_id}
        )
        
        return [
            {"department_id": row.department_id, "name": row.name, "is_stem": row.is_stem}
            for row in result.fetchall()
        ]
    
    @classmethod
    async def get_programmes(
        cls, 
        university_id: str, 
        department_id: str, 
        session: AsyncSession,
        level: str = "undergraduate"
    ) -> List[dict]:
        """
        Get all programmes for a department (for frontend dropdowns).
        
        Returns lightweight dict format for API responses.
        """
        from sqlalchemy import text
        
        query = """
            SELECT p.programme_id, p.name, p.level, p.duration_years
            FROM programmes p
            JOIN departments d ON p.department_id = d.id
            JOIN faculties f ON d.faculty_id = f.id
            JOIN universities u ON f.university_id = u.id
            WHERE u.university_id = :university_id 
              AND d.department_id = :department_id
              AND p.level = :level
              AND u.is_active = true 
              AND d.is_active = true
              AND p.is_active = true
            ORDER BY p.display_order
        """
        
        result = await session.execute(
            text(query), 
            {"university_id": university_id, "department_id": department_id, "level": level}
        )
        
        return [
            {
                "programme_id": row.programme_id, 
                "name": row.name, 
                "level": row.level,
                "duration_years": row.duration_years
            }
            for row in result.fetchall()
        ]
