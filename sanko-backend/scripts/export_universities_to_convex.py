"""
Export University Data from Neon PostgreSQL to JSON.

This script exports all university, faculty, and department data from Neon
in a format that can be directly seeded into Convex.

Usage:
    cd sanko-backend
    python scripts/export_universities_to_convex.py

Output:
    Creates 'universities_export.json' with data ready for Convex seeding.
"""

import os
import json
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set. Please check your .env file.")
    exit(1)


async def export_universities():
    """Export all university data from Neon PostgreSQL."""
    import asyncpg
    
    # Convert standard PostgreSQL URL to asyncpg format
    url = DATABASE_URL
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgres://", 1)
    
    print(f"Connecting to database...")
    
    try:
        conn = await asyncpg.connect(url)
        print("Connected successfully!")
        
        # Fetch all universities
        universities_rows = await conn.fetch("""
            SELECT 
                university_id, name, short_name, country,
                default_citation_style, spelling_variant, unit_system
            FROM universities
            WHERE is_active = true
            ORDER BY name
        """)
        
        print(f"Found {len(universities_rows)} universities")
        
        universities = []
        
        for uni_row in universities_rows:
            uni_id = uni_row['university_id']
            print(f"  Processing: {uni_row['name']}")
            
            # Fetch faculties for this university
            faculties_rows = await conn.fetch("""
                SELECT f.faculty_id, f.name, f.short_name
                FROM faculties f
                JOIN universities u ON f.university_id = u.id
                WHERE u.university_id = $1 AND f.is_active = true
                ORDER BY f.display_order
            """, uni_id)
            
            faculties = []
            
            for fac_row in faculties_rows:
                fac_id = fac_row['faculty_id']
                
                # Fetch departments for this faculty
                departments_rows = await conn.fetch("""
                    SELECT d.department_id, d.name, d.is_stem
                    FROM departments d
                    JOIN faculties f ON d.faculty_id = f.id
                    JOIN universities u ON f.university_id = u.id
                    WHERE u.university_id = $1 AND f.faculty_id = $2 AND d.is_active = true
                    ORDER BY d.display_order
                """, uni_id, fac_id)
                
                departments = [
                    {
                        "departmentId": dept['department_id'],
                        "name": dept['name'],
                        "isStem": dept['is_stem']
                    }
                    for dept in departments_rows
                ]
                
                faculties.append({
                    "facultyId": fac_row['faculty_id'],
                    "name": fac_row['name'],
                    "shortName": fac_row['short_name'],
                    "departments": departments
                })
                
                print(f"    - {fac_row['name']}: {len(departments)} departments")
            
            universities.append({
                "universityId": uni_row['university_id'],
                "name": uni_row['name'],
                "shortName": uni_row['short_name'],
                "country": uni_row['country'],
                "defaultCitationStyle": uni_row['default_citation_style'],
                "spellingVariant": uni_row['spelling_variant'],
                "unitSystem": uni_row['unit_system'],
                "faculties": faculties
            })
        
        await conn.close()
        
        # Save to JSON file
        output_path = Path(__file__).parent.parent / "universities_export.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"universities": universities}, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Exported to: {output_path}")
        print(f"   Universities: {len(universities)}")
        total_faculties = sum(len(u['faculties']) for u in universities)
        total_departments = sum(
            len(d['departments']) 
            for u in universities 
            for d in u['faculties']
        )
        print(f"   Faculties: {total_faculties}")
        print(f"   Departments: {total_departments}")
        
        return universities
        
    except Exception as e:
        print(f"ERROR: Failed to connect or query database: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(export_universities())
