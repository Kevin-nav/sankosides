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
        status: v.string(), // draft, generating, completed
        sessionId: v.optional(v.string()), // Reference to playground session UUID (from backend)

        // Generated slides data (JSON structure)
        slidesData: v.optional(v.any()),

        createdAt: v.number(),
        updatedAt: v.number(),
    }).index("by_user_id", ["userId"]),

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
});
