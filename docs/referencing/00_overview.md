# Reference System Implementation - Overview

## Introduction
This document series provides complete implementation details for adding a comprehensive referencing system to SankoSlides. The system supports inline citations, automatic References slides, configurable Thank You slides, and university-specific formatting rules.

---

## Key Decisions Summary

| Topic | Decision |
|-------|----------|
| **New Slide Types** | `REFERENCES` (auto-generated), `THANK_YOU` (configurable) |
| **Inline Citations** | Author-year for Harvard/APA/Chicago, numbered for IEEE |
| **Citation Verification** | New `Citation Auditor` agent after Refiner |
| **DOI Validation** | Use CrossRef API for verification |
| **Image Captions** | "Figure {n}: {caption}" format below images |
| **References Slide** | Auto-generated at end from all slide citations |
| **Multiple Citations** | Supported: `(Smith, 2024; Jones, 2023)` |
| **University Config** | Each university has own formatting rules |
| **Database Templates** | Add `university_id` column for customization |
| **Default Config** | APA style, American English for unaffiliated users |

---

## Phase Documents

### [Phase 1: Core Slide Types](./phase1_core_slide_types.md)
- Add `REFERENCES` and `THANK_YOU` to `SlideContentType` enum
- Create template layouts for both
- Database migration for `university_id` on templates
- Auto-generation logic in pipeline
- Seed default templates

**Estimated Effort**: 3-4 hours

---

### [Phase 2: Citation System & Auditor Agent](./phase2_citation_system.md)
- Add `ReferenceConfig` to `FormattingRules`
- Create `Citation Auditor` agent
- DOI Validator tool for verification
- Inline citation extraction utilities
- HTML citation formatting via render service
- Zero-hallucination verification

**Estimated Effort**: 4-5 hours

---

### [Phase 3: Image Citations & Captions](./phase3_image_citations.md)
- Add `ImageCitation` model
- Add `ImageConfig` to `FormattingRules`
- Figure numbering service
- Update image templates with caption/attribution
- Include image sources in References slide

**Estimated Effort**: 2-3 hours

---

## Architecture Changes

### Pipeline Flow (Updated)
```
Clarifier → Outliner → Planner → Refiner → [Citation Auditor] → Generator → Visual QA
                                              (NEW)
```

### Data Flow
```
PlannedSlide.citation_queries
        ↓
Refiner: Search → Create CitationMetadata
        ↓
Citation Auditor: Verify → Remove unverified
        ↓
Generator: Render slides with inline citations
        ↓
Auto-generate References slide from all CitationMetadata
        ↓
Auto-generate Thank You slide
```

---

## Configuration Hierarchy

```
University Default (FormattingRules)
    └── references: ReferenceConfig
    └── images: ImageConfig
    └── thank_you: ThankYouConfig
            ↓
User Settings (can override)
    └── thank_you.show_logo
    └── thank_you.show_presenter_name
            ↓
Per-Project (can override)
    └── Any setting
```

---

## Database Changes

### New Migration
```sql
ALTER TABLE slide_templates 
ADD COLUMN university_id VARCHAR(50) NULL;

CREATE INDEX ix_slide_templates_university_id 
ON slide_templates(university_id);
```

### No Other DB Changes
- `ReferenceConfig`, `ImageConfig`, `ThankYouConfig` are stored in code-based `FormattingRules`
- University configs use the existing `UniversityRegistry` pattern

---

## UMaT Configuration (First University)

Based on the UMaT Thesis Guide, the configuration is:

| Rule | Value |
|------|-------|
| Citation Style | Harvard |
| Spelling | British English |
| Units | SI with spacing |
| Figure Caption | Below figure |
| Table Caption | Above table |
| References | Last slide, alphabetical |
| Inline Format | (Author, Year) |

---

## Files Index

### New Files
| Path | Purpose |
|------|---------|
| `app/crew/agents/citation_auditor.py` | Citation verification agent |
| `app/crew/tools/doi_validator.py` | DOI validation via CrossRef |
| `app/services/citation_utils.py` | Citation extraction regex |
| `app/services/figure_numbering.py` | Figure numbering service |
| `app/templates/layouts/references.py` | References slide template |
| `app/templates/layouts/thank_you.py` | Thank You slide template |

### Modified Files
| Path | Changes |
|------|---------|
| `app/models/schemas.py` | Add slide types, ImageCitation |
| `app/core/university_configs/base.py` | Add config classes |
| `app/templates/__init__.py` | Register new templates |
| `app/crew/flows/slide_generation.py` | Auditor step, auto-generation |
| `app/crew/agents/refiner.py` | Image attribution instructions |
| `sanko-render-service/src/services/citation.service.js` | HTML format |
| `sanko-render-service/src/routes/citation.routes.js` | Format param |

---

## Testing Strategy

### Unit Tests
- Citation regex extraction accuracy
- DOI validation response handling
- Figure numbering assignment
- Citation formatting output

### Integration Tests
- Full pipeline with citations
- References slide generation
- Thank You slide configuration
- University-specific formatting

### Manual Verification
- Visual inspection of rendered References slide
- Check italics in Harvard/APA citations
- Verify IEEE numbered format
- Confirm image captions appear correctly

---

## Handover Notes for Implementing Agent

1. **Start with Phase 1** - The core slide types are foundational
2. **Use existing patterns** - Follow the existing template structure
3. **Test incrementally** - Each phase should be testable independently
4. **UMaT first** - Use UMaT as the first university configuration
5. **Renderer is key** - The citation formatting relies on `sanko-render-service`
6. **Zero hallucination** - The Citation Auditor MUST remove unverified citations

---

## Questions Answered During Planning

All questions were resolved during discussion. Key clarifications:
- No superscripts in slides (use author-year or bracket numbers)
- Simple figure numbering (Figure 1, not Figure 2.1)
- Thank You slide is separate from Conclusion
- Each university can have custom rules
- Default config for unaffiliated users is APA/American English
