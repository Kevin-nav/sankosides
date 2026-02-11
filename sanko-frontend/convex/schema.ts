import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
    users: defineTable({
        firebaseUid: v.string(), // Unique index linked to Firebase Auth
        email: v.string(),
        displayName: v.optional(v.string()),
        photoUrl: v.optional(v.string()),

        // Abstracted JSON fields
        universityProfile: v.optional(v.any()),
        preferences: v.optional(v.any()),

        subscriptionTier: v.optional(v.string()),

        createdAt: v.number(), // Unix timestamp
        updatedAt: v.number(),
    }).index("by_firebase_uid", ["firebaseUid"]),

    // Projects table
    projects: defineTable({
        userId: v.id("users"), // Reference to Convex User ID
        title: v.string(),
        description: v.optional(v.string()),
        thumbnailUrl: v.optional(v.string()),
        status: v.string(), // draft, generating, completed, archived
        archiveSourceStatus: v.optional(v.string()), // status to restore when unarchiving
        sessionId: v.optional(v.string()), // Reference to playground session UUID (from backend)

        // Generated slides data (JSON structure)
        slidesData: v.optional(v.any()),

        createdAt: v.number(),
        updatedAt: v.number(),
    }).index("by_user_id", ["userId"])
        .index("by_user_updated_at", ["userId", "updatedAt"]),

    // Templates table (ported from backend SlideTemplate)
    templates: defineTable({
        templateId: v.string(), // e.g. 'title', 'two_col'
        name: v.string(),
        description: v.optional(v.string()),
        contentType: v.string(), // 'title', 'content', 'visual'
        category: v.string(), // 'general', 'academic'

        // Template content
        htmlTemplate: v.string(), // Jinja2 string
        cssStyles: v.optional(v.string()),

        // Metadata
        isActive: v.boolean(),
        isSystem: v.boolean(),
        version: v.string(),

        createdAt: v.number(),
        updatedAt: v.number(),
    }).index("by_template_id", ["templateId"])
        .index("by_category", ["category"]),

    // Theme Palettes (ported from backend ThemePalette)
    themePalettes: defineTable({
        name: v.string(),
        category: v.string(),
        colors: v.any(), // JSON object of colors
        isDefault: v.boolean(),
        isSystem: v.boolean(),
        createdAt: v.number(),
        updatedAt: v.number(),
    }),

    // Theme Configs (ported from backend ThemeConfig)
    themeConfigs: defineTable({
        themeId: v.string(),
        name: v.string(),
        description: v.optional(v.string()),
        paletteId: v.optional(v.id("themePalettes")),
        typography: v.optional(v.any()),
        spacing: v.optional(v.any()),
        borders: v.optional(v.any()),
        cssOverrides: v.optional(v.string()),
        layoutStyle: v.optional(v.string()),
        isActive: v.boolean(),
        isSystem: v.boolean(),
        createdAt: v.number(),
        updatedAt: v.number(),
    }).index("by_theme_id", ["themeId"]),

    // =========================================================================
    // University Hierarchy (migrated from Neon PostgreSQL)
    // =========================================================================

    // Universities table
    universities: defineTable({
        universityId: v.string(), // e.g., 'knust', 'ug'
        name: v.string(),
        shortName: v.string(),
        country: v.string(),
        defaultCitationStyle: v.string(), // 'apa', 'ieee', etc.
        spellingVariant: v.string(), // 'british', 'american'
        unitSystem: v.string(), // 'metric', 'imperial'
        createdAt: v.number(),
        updatedAt: v.number(),
    }).index("by_university_id", ["universityId"]),

    // Faculties table
    faculties: defineTable({
        universityId: v.id("universities"),
        facultyId: v.string(), // e.g., 'engineering'
        name: v.string(),
        shortName: v.string(),
        createdAt: v.number(),
        updatedAt: v.number(),
    }).index("by_university", ["universityId"])
        .index("by_faculty_id", ["facultyId"]),

    // Departments table
    departments: defineTable({
        facultyId: v.id("faculties"),
        departmentId: v.string(), // e.g., 'computer_engineering'
        name: v.string(),
        isStem: v.boolean(),
        createdAt: v.number(),
        updatedAt: v.number(),
    }).index("by_faculty", ["facultyId"])
        .index("by_department_id", ["departmentId"]),

    // =========================================================================
    // Citation Cache (migrated from Neon PostgreSQL)
    // =========================================================================

    cachedCitations: defineTable({
        queryHash: v.string(), // SHA256 of normalized query
        normalizedQuery: v.string(),
        citationData: v.any(), // Array of citation objects
        provider: v.string(), // 'semantic_scholar', 'crossref', etc.
        createdAt: v.number(),
        expiresAt: v.number(), // TTL for cache invalidation
    }).index("by_query_hash", ["queryHash"]),

    // =========================================================================
    // Layout Presets (migrated from Neon PostgreSQL)
    // =========================================================================

    layoutPresets: defineTable({
        presetId: v.string(),
        name: v.string(),
        description: v.optional(v.string()),
        config: v.any(), // Layout configuration JSON
        isSystem: v.boolean(),
        createdAt: v.number(),
        updatedAt: v.number(),
    }).index("by_preset_id", ["presetId"]),

    // =========================================================================
    // Survey Responses
    // =========================================================================

    surveyResponses: defineTable({
        userId: v.optional(v.id("users")),
        responses: v.any(), // Survey answers JSON
        createdAt: v.number(),
    }),

    // =========================================================================
    // Generation Progress (Real-time AI Generation Tracking)
    // =========================================================================

    generationProgress: defineTable({
        projectId: v.id("projects"),
        sessionId: v.string(), // Playground session UUID from backend

        // Progress tracking
        currentStep: v.string(), // 'initializing', 'parsing', 'outlining', 'generating', 'rendering', 'complete', 'error'
        stepProgress: v.number(), // 0-100 percentage

        // Slide generation progress
        currentSlideIndex: v.optional(v.number()),
        totalSlides: v.optional(v.number()),

        // Status messages
        message: v.optional(v.string()), // Current action description
        error: v.optional(v.string()), // Error message if failed

        // Blueprint Data (Added for polling migration)
        blueprint: v.optional(v.any()), // Generated skeleton
        clarificationStatus: v.optional(v.string()), // e.g. 'blueprint_ready'

        // Timestamps
        createdAt: v.number(),
        updatedAt: v.number(),
    }).index("by_project_id", ["projectId"])
        .index("by_session_id", ["sessionId"]),
});
