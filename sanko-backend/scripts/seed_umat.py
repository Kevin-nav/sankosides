"""
Seed script for UMaT University Configuration.

Run this script after applying migrations to populate the database
with University of Mines and Technology (UMaT) data.

Usage:
    cd sanko-backend
    python -m scripts.seed_umat

Or via alembic data migration:
    alembic upgrade head  # Creates tables
    python -m scripts.seed_umat  # Populates data
"""

import asyncio
import json
from uuid import uuid4
from datetime import datetime, UTC

# Database connection will be configured based on environment
DATABASE_URL = None  # Set from environment or config

# =============================================================================
# UMaT SEED DATA
# =============================================================================

UMAT_UNIVERSITY = {
    "university_id": "umat",
    "name": "University of Mines and Technology",
    "short_name": "UMaT",
    "country": "Ghana",
    "default_citation_style": "harvard",
    "spelling_variant": "british",
    "unit_system": "si",
    "primary_color": "#1E3A5F",
    "secondary_color": "#D4AF37",
    "logo_url": "/assets/universities/umat-logo.png",
    "formatting_rules": {
        "figure_caption_position": "below",
        "table_caption_position": "above",
        "reference_placement": "last_slide",
        "acronym_first_use": "spell_out",
        "number_unit_spacing": True,
        # Image configuration (Phase 3)
        "images": {
            "caption_format": "Figure {n}: {caption}",
            "source_format": "Source: {source}",
            "attribution_position": "below_caption",
            "include_in_references": True,
            "numbering_prefix": "Figure",
        },
    },
    "compliance_checking_enabled": False,
    "custom_templates_enabled": False,
    "is_active": True,
}

UMAT_FACULTIES = [
    {
        "faculty_id": "fmmt",
        "name": "Faculty of Mining and Minerals Technology",
        "short_name": "FMMT",
        "display_order": 1,
    },
    {
        "faculty_id": "foe",
        "name": "Faculty of Engineering",
        "short_name": "FoE",
        "display_order": 2,
    },
    {
        "faculty_id": "fges",
        "name": "Faculty of Geosciences and Environmental Studies",
        "short_name": "FGES",
        "display_order": 3,
    },
    {
        "faculty_id": "fcams",
        "name": "Faculty of Computing and Mathematical Sciences",
        "short_name": "FCaMS",
        "display_order": 4,
    },
    {
        "faculty_id": "fims",
        "name": "Faculty of Integrated Management Science",
        "short_name": "FIMS",
        "display_order": 5,
    },
    {
        "faculty_id": "spets",
        "name": "School of Petroleum Studies",
        "short_name": "SPetS",
        "display_order": 6,
    },
]

# Departments organized by faculty_id
UMAT_DEPARTMENTS = {
    "fmmt": [
        {
            "department_id": "mining_engineering",
            "name": "Mining Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "mine_layout", "geological_cross_section", "drilling_pattern",
                "blast_design", "excavation_flow", "ventilation_network", "stope_design"
            ],
            "common_equation_domains": [
                "rock_mechanics", "mine_ventilation", "drilling_blasting",
                "ore_reserve_estimation", "mine_economics", "ground_control"
            ],
            "preferred_journals": [
                "Ghana Mining Journal", "Mining Engineering",
                "International Journal of Mining Science and Technology"
            ],
            "display_order": 1,
        },
        {
            "department_id": "minerals_engineering",
            "name": "Minerals Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "process_flowchart", "separation_circuit", "leaching_process",
                "flotation_circuit", "comminution_circuit", "thickener_design"
            ],
            "common_equation_domains": [
                "thermodynamics", "mineral_processing", "metallurgy",
                "mass_balance", "grade_recovery", "liberation_kinetics"
            ],
            "preferred_journals": [
                "Minerals Engineering", "Hydrometallurgy",
                "Mineral Processing and Extractive Metallurgy Review"
            ],
            "display_order": 2,
        },
    ],
    "foe": [
        {
            "department_id": "mechanical_engineering",
            "name": "Mechanical Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "machine_design", "thermodynamic_cycle", "stress_strain_diagram",
                "gear_train", "hydraulic_system", "free_body_diagram", "heat_exchanger"
            ],
            "common_equation_domains": [
                "mechanics", "thermodynamics", "fluid_dynamics",
                "heat_transfer", "machine_design", "vibrations"
            ],
            "preferred_journals": [
                "Journal of Mechanical Engineering",
                "International Journal of Heat and Mass Transfer"
            ],
            "display_order": 1,
        },
        {
            "department_id": "electrical_electronic_engineering",
            "name": "Electrical and Electronic Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "circuit_diagram", "block_diagram", "signal_flow_graph",
                "power_system_diagram", "control_system_block", "timing_diagram"
            ],
            "common_equation_domains": [
                "circuit_analysis", "electromagnetics", "signal_processing",
                "power_systems", "control_theory", "digital_systems"
            ],
            "preferred_journals": [
                "IEEE Transactions on Power Systems", "IEEE Communications Magazine"
            ],
            "display_order": 2,
        },
        {
            "department_id": "renewable_energy_engineering",
            "name": "Renewable Energy Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "solar_pv_system", "wind_turbine_diagram", "biomass_conversion",
                "energy_flow_diagram", "grid_integration", "battery_storage"
            ],
            "common_equation_domains": [
                "photovoltaics", "wind_energy", "energy_storage",
                "thermodynamics", "energy_economics", "power_electronics"
            ],
            "preferred_journals": [
                "Renewable Energy", "Solar Energy", "Applied Energy"
            ],
            "display_order": 3,
        },
    ],
    "fges": [
        {
            "department_id": "geological_engineering",
            "name": "Geological Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "geological_map", "stratigraphic_column", "cross_section",
                "ore_body_model", "hydrogeological_section", "stereonet"
            ],
            "common_equation_domains": [
                "hydrogeology", "geotechnics", "ore_genesis",
                "structural_geology", "groundwater_flow", "soil_mechanics"
            ],
            "preferred_journals": [
                "Engineering Geology", "Journal of African Earth Sciences", "Hydrogeology Journal"
            ],
            "display_order": 1,
        },
        {
            "department_id": "geomatic_engineering",
            "name": "Geomatic Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "survey_plan", "gis_map", "remote_sensing_image",
                "cadastral_map", "coordinate_system", "dtm_surface"
            ],
            "common_equation_domains": [
                "geodesy", "photogrammetry", "coordinate_transformation",
                "gis_analysis", "surveying", "map_projection"
            ],
            "preferred_journals": [
                "Survey Review", "ISPRS Journal of Photogrammetry and Remote Sensing", "Land Use Policy"
            ],
            "display_order": 2,
        },
        {
            "department_id": "environmental_safety_engineering",
            "name": "Environmental and Safety Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "eia_flowchart", "waste_management_diagram", "safety_hierarchy",
                "environmental_monitoring", "risk_matrix", "bow_tie_diagram"
            ],
            "common_equation_domains": [
                "environmental_chemistry", "toxicology", "risk_assessment",
                "air_quality", "water_quality", "noise_modeling"
            ],
            "preferred_journals": [
                "Journal of Environmental Management", "Safety Science", "Environmental Pollution"
            ],
            "display_order": 3,
        },
    ],
    "fcams": [
        {
            "department_id": "computer_science_engineering",
            "name": "Computer Science and Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "flowchart", "uml_class_diagram", "uml_sequence_diagram",
                "system_architecture", "network_topology", "er_diagram", "state_machine", "neural_network"
            ],
            "common_equation_domains": [
                "algorithms", "complexity_analysis", "machine_learning",
                "cryptography", "linear_algebra", "discrete_mathematics"
            ],
            "preferred_journals": [
                "IEEE Transactions on Computers", "ACM Computing Surveys", "Artificial Intelligence"
            ],
            "display_order": 1,
        },
        {
            "department_id": "mathematical_sciences",
            "name": "Mathematical Sciences",
            "is_stem": True,
            "common_diagram_types": [
                "graph", "statistical_chart", "probability_distribution",
                "optimization_surface", "mathematical_model", "phase_portrait"
            ],
            "common_equation_domains": [
                "calculus", "linear_algebra", "statistics",
                "probability", "optimization", "differential_equations", "numerical_analysis"
            ],
            "preferred_journals": [
                "Journal of Mathematical Analysis and Applications",
                "Statistics and Computing", "Journal of Statistical Planning and Inference"
            ],
            "display_order": 2,
        },
    ],
    "fims": [
        {
            "department_id": "management_studies",
            "name": "Management Studies",
            "is_stem": False,
            "common_diagram_types": [
                "supply_chain_diagram", "organizational_chart", "process_flow",
                "financial_model", "market_analysis", "swot_matrix", "gantt_chart"
            ],
            "common_equation_domains": [
                "financial_mathematics", "econometrics", "operations_research",
                "statistics", "time_series"
            ],
            "preferred_journals": [
                "Journal of Business Research", "Transportation Research", "Journal of Finance"
            ],
            "display_order": 1,
        },
        {
            "department_id": "technical_communication",
            "name": "Technical Communication",
            "is_stem": False,
            "common_diagram_types": [],
            "common_equation_domains": [],
            "preferred_journals": [],
            "display_order": 2,
        },
    ],
    "spets": [
        {
            "department_id": "petroleum_natural_gas_engineering",
            "name": "Petroleum and Natural Gas Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "well_schematic", "reservoir_model", "drilling_rig_diagram",
                "production_system", "pipeline_network", "completion_diagram"
            ],
            "common_equation_domains": [
                "reservoir_engineering", "drilling_engineering", "production_engineering",
                "fluid_mechanics", "well_testing", "enhanced_oil_recovery"
            ],
            "preferred_journals": [
                "SPE Journal", "Journal of Petroleum Science and Engineering", "Petroleum Geoscience"
            ],
            "display_order": 1,
        },
        {
            "department_id": "petroleum_geosciences",
            "name": "Petroleum Geosciences and Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "seismic_section", "stratigraphic_trap", "source_rock_diagram",
                "migration_path", "well_log", "basin_model"
            ],
            "common_equation_domains": [
                "geophysics", "petrophysics", "seismology",
                "reservoir_characterization", "basin_modeling"
            ],
            "preferred_journals": [
                "AAPG Bulletin", "Marine and Petroleum Geology", "Geophysics"
            ],
            "display_order": 2,
        },
        {
            "department_id": "chemical_petrochemical_engineering",
            "name": "Chemical and Petrochemical Engineering",
            "is_stem": True,
            "common_diagram_types": [
                "process_flow_diagram", "piping_instrumentation_diagram",
                "reaction_mechanism", "distillation_column", "reactor_design", "heat_mass_balance"
            ],
            "common_equation_domains": [
                "reaction_engineering", "mass_transfer", "thermodynamics",
                "process_control", "separation_processes", "reactor_design"
            ],
            "preferred_journals": [
                "Chemical Engineering Science", "Fuel", "Industrial & Engineering Chemistry Research"
            ],
            "display_order": 3,
        },
    ],
}

# Programmes organized by department_id
UMAT_PROGRAMMES = {
    # FMMT
    "mining_engineering": [
        {"programme_id": "bsc_mining_engineering", "name": "BSc Mining Engineering", "level": "undergraduate", "duration_years": 4},
    ],
    "minerals_engineering": [
        {"programme_id": "bsc_minerals_engineering", "name": "BSc Minerals Engineering", "level": "undergraduate", "duration_years": 4},
    ],
    # FoE
    "mechanical_engineering": [
        {"programme_id": "bsc_mechanical_engineering", "name": "BSc Mechanical Engineering", "level": "undergraduate", "duration_years": 4},
    ],
    "electrical_electronic_engineering": [
        {"programme_id": "bsc_electrical_electronic_engineering", "name": "BSc Electrical and Electronic Engineering", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_telecommunication_engineering", "name": "BSc Telecommunication Engineering", "level": "undergraduate", "duration_years": 4},
    ],
    "renewable_energy_engineering": [
        {"programme_id": "bsc_renewable_energy_engineering", "name": "BSc Renewable Energy Engineering", "level": "undergraduate", "duration_years": 4},
    ],
    # FGES
    "geological_engineering": [
        {"programme_id": "bsc_geological_engineering", "name": "BSc Geological Engineering", "level": "undergraduate", "duration_years": 4},
    ],
    "geomatic_engineering": [
        {"programme_id": "bsc_geomatic_engineering", "name": "BSc Geomatic Engineering", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_land_administration", "name": "BSc Land Administration and Information Systems", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_spatial_planning", "name": "BSc Spatial Planning", "level": "undergraduate", "duration_years": 4},
    ],
    "environmental_safety_engineering": [
        {"programme_id": "bsc_environmental_safety_engineering", "name": "BSc Environmental and Safety Engineering", "level": "undergraduate", "duration_years": 4},
    ],
    # FCaMS
    "computer_science_engineering": [
        {"programme_id": "bsc_computer_science_engineering", "name": "BSc Computer Science and Engineering", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_cyber_security", "name": "BSc Cyber Security", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_information_systems_technology", "name": "BSc Information Systems and Technology", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_robotics_ai", "name": "BSc Robotics Engineering and Artificial Intelligence", "level": "undergraduate", "duration_years": 4},
    ],
    "mathematical_sciences": [
        {"programme_id": "bsc_mathematics", "name": "BSc Mathematics", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_statistical_data_science", "name": "BSc Statistical Data Science", "level": "undergraduate", "duration_years": 4},
    ],
    # FIMS
    "management_studies": [
        {"programme_id": "bsc_logistics_transport_management", "name": "BSc Logistics and Transport Management", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_economics_industrial_organisation", "name": "BSc Economics and Industrial Organisation", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_finance_data_science", "name": "BSc Finance and Data Science", "level": "undergraduate", "duration_years": 4},
    ],
    "technical_communication": [],  # No BSc programmes
    # SPetS
    "petroleum_natural_gas_engineering": [
        {"programme_id": "bsc_petroleum_engineering", "name": "BSc Petroleum Engineering", "level": "undergraduate", "duration_years": 4, "is_fee_paying": True},
        {"programme_id": "bsc_natural_gas_engineering", "name": "BSc Natural Gas Engineering", "level": "undergraduate", "duration_years": 4},
    ],
    "petroleum_geosciences": [
        {"programme_id": "bsc_petroleum_geosciences_engineering", "name": "BSc Petroleum Geosciences and Engineering", "level": "undergraduate", "duration_years": 4},
    ],
    "chemical_petrochemical_engineering": [
        {"programme_id": "bsc_petroleum_refining_petrochemical", "name": "BSc Petroleum Refining and Petrochemical Engineering", "level": "undergraduate", "duration_years": 4},
        {"programme_id": "bsc_chemical_engineering", "name": "BSc Chemical Engineering", "level": "undergraduate", "duration_years": 4},
    ],
}


async def seed_umat_data(db_session):
    """
    Seed the database with UMaT university data.
    
    Args:
        db_session: SQLAlchemy async session
    """
    from sqlalchemy import text
    
    print("🎓 Seeding UMaT University data...")
    
    # Check if UMaT already exists
    result = await db_session.execute(
        text("SELECT id FROM universities WHERE university_id = :uid"),
        {"uid": "umat"}
    )
    existing = result.fetchone()
    
    if existing:
        print("  ⚠️ UMaT already exists in database, skipping...")
        return
    
    # Insert university
    university_id = uuid4()
    await db_session.execute(
        text("""
            INSERT INTO universities (
                id, university_id, name, short_name, country,
                default_citation_style, spelling_variant, unit_system,
                primary_color, secondary_color, logo_url,
                formatting_rules, compliance_checking_enabled, custom_templates_enabled, is_active
            ) VALUES (
                :id, :university_id, :name, :short_name, :country,
                :default_citation_style, :spelling_variant, :unit_system,
                :primary_color, :secondary_color, :logo_url,
                :formatting_rules, :compliance_checking_enabled, :custom_templates_enabled, :is_active
            )
        """),
        {
            "id": university_id,
            **UMAT_UNIVERSITY,
            "formatting_rules": json.dumps(UMAT_UNIVERSITY["formatting_rules"]),
        }
    )
    print(f"  ✅ Created university: {UMAT_UNIVERSITY['name']}")
    
    # Insert faculties
    faculty_ids = {}
    for faculty_data in UMAT_FACULTIES:
        faculty_uuid = uuid4()
        faculty_ids[faculty_data["faculty_id"]] = faculty_uuid
        
        await db_session.execute(
            text("""
                INSERT INTO faculties (
                    id, university_id, faculty_id, name, short_name, display_order, is_active
                ) VALUES (
                    :id, :university_id, :faculty_id, :name, :short_name, :display_order, true
                )
            """),
            {
                "id": faculty_uuid,
                "university_id": university_id,
                **faculty_data
            }
        )
        print(f"  ✅ Created faculty: {faculty_data['short_name']}")
    
    # Insert departments
    department_ids = {}
    for faculty_id, departments in UMAT_DEPARTMENTS.items():
        faculty_uuid = faculty_ids[faculty_id]
        
        for dept_data in departments:
            dept_uuid = uuid4()
            department_ids[dept_data["department_id"]] = dept_uuid
            
            await db_session.execute(
                text("""
                    INSERT INTO departments (
                        id, faculty_id, department_id, name, is_stem,
                        common_diagram_types, common_equation_domains, preferred_journals,
                        citation_style_override, display_order, is_active
                    ) VALUES (
                        :id, :faculty_id, :department_id, :name, :is_stem,
                        :common_diagram_types, :common_equation_domains, :preferred_journals,
                        :citation_style_override, :display_order, true
                    )
                """),
                {
                    "id": dept_uuid,
                    "faculty_id": faculty_uuid,
                    "department_id": dept_data["department_id"],
                    "name": dept_data["name"],
                    "is_stem": dept_data["is_stem"],
                    "common_diagram_types": json.dumps(dept_data.get("common_diagram_types", [])),
                    "common_equation_domains": json.dumps(dept_data.get("common_equation_domains", [])),
                    "preferred_journals": json.dumps(dept_data.get("preferred_journals", [])),
                    "citation_style_override": dept_data.get("citation_style_override"),
                    "display_order": dept_data.get("display_order", 0),
                }
            )
        print(f"    ✅ Created {len(departments)} departments for {faculty_id.upper()}")
    
    # Insert programmes
    total_programmes = 0
    for dept_id, programmes in UMAT_PROGRAMMES.items():
        if dept_id not in department_ids:
            continue
            
        dept_uuid = department_ids[dept_id]
        
        for prog_data in programmes:
            await db_session.execute(
                text("""
                    INSERT INTO programmes (
                        id, department_id, programme_id, name, level,
                        duration_years, is_fee_paying, display_order, is_active
                    ) VALUES (
                        :id, :department_id, :programme_id, :name, :level,
                        :duration_years, :is_fee_paying, :display_order, true
                    )
                """),
                {
                    "id": uuid4(),
                    "department_id": dept_uuid,
                    "programme_id": prog_data["programme_id"],
                    "name": prog_data["name"],
                    "level": prog_data["level"],
                    "duration_years": prog_data.get("duration_years", 4),
                    "is_fee_paying": prog_data.get("is_fee_paying", False),
                    "display_order": total_programmes,
                }
            )
            total_programmes += 1
    
    print(f"  ✅ Created {total_programmes} programmes")
    
    await db_session.commit()
    print("🎉 UMaT seeding complete!")


# Entry point for running as script
if __name__ == "__main__":
    print("Run this script via: python -m scripts.seed_umat")
    print("Or import and call seed_umat_data(session) directly")
