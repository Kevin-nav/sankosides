import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

// ============================================================================
// TEMPLATES
// ============================================================================

export const getTemplateById = query({
    args: { templateId: v.string() },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("templates")
            .withIndex("by_template_id", (q) => q.eq("templateId", args.templateId))
            .unique();
    },
});

export const getTemplateByIds = query({
    args: { templateIds: v.array(v.string()) },
    handler: async (ctx, args) => {
        const results = [];
        for (const tid of args.templateIds) {
            const template = await ctx.db
                .query("templates")
                .withIndex("by_template_id", (q) => q.eq("templateId", tid))
                .unique();
            if (template) results.push(template);
        }
        return results;
    },
});

// Upsert template (Migration safe)
export const upsertTemplate = mutation({
    args: {
        templateId: v.string(),
        name: v.string(),
        description: v.optional(v.string()),
        contentType: v.string(),
        category: v.string(),
        htmlTemplate: v.string(),
        cssStyles: v.optional(v.string()),
        isActive: v.boolean(),
        isSystem: v.boolean(),
        version: v.string(),
    },
    handler: async (ctx, args) => {
        const existing = await ctx.db
            .query("templates")
            .withIndex("by_template_id", (q) => q.eq("templateId", args.templateId))
            .unique();

        if (existing) {
            await ctx.db.patch(existing._id, {
                name: args.name,
                description: args.description,
                contentType: args.contentType,
                category: args.category,
                htmlTemplate: args.htmlTemplate,
                cssStyles: args.cssStyles,
                isActive: args.isActive,
                isSystem: args.isSystem,
                version: args.version,
                updatedAt: Date.now(),
            });
            return existing._id;
        } else {
            const now = Date.now();
            return await ctx.db.insert("templates", {
                ...args,
                createdAt: now,
                updatedAt: now,
            });
        }
    },
});

// ============================================================================
// THEMES
// ============================================================================

export const getThemeConfig = query({
    args: { themeId: v.string() },
    handler: async (ctx, args) => {
        const config = await ctx.db
            .query("themeConfigs")
            .withIndex("by_theme_id", (q) => q.eq("themeId", args.themeId))
            .unique();

        if (!config) return null;

        // Also fetch the palette if it exists
        let palette = null;
        if (config.paletteId) {
            palette = await ctx.db.get(config.paletteId);
        }

        return { config, palette };
    },
});

export const upsertThemePalette = mutation({
    args: {
        name: v.string(),
        category: v.string(),
        colors: v.any(),
        isDefault: v.boolean(),
        isSystem: v.boolean(),
    },
    handler: async (ctx, args) => {
        // Find by name + category as a unique key for pallets
        const existing = await ctx.db
            .query("themePalettes")
            .filter((q) => q.and(
                q.eq(q.field("name"), args.name),
                q.eq(q.field("category"), args.category)
            ))
            .unique();

        if (existing) {
            await ctx.db.patch(existing._id, {
                colors: args.colors,
                isDefault: args.isDefault,
                isSystem: args.isSystem,
                updatedAt: Date.now(),
            });
            return existing._id;
        } else {
            const now = Date.now();
            return await ctx.db.insert("themePalettes", {
                ...args,
                createdAt: now,
                updatedAt: now,
            });
        }
    },
});

export const upsertThemeConfig = mutation({
    args: {
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
    },
    handler: async (ctx, args) => {
        const existing = await ctx.db
            .query("themeConfigs")
            .withIndex("by_theme_id", (q) => q.eq("themeId", args.themeId))
            .unique();

        if (existing) {
            await ctx.db.patch(existing._id, {
                name: args.name,
                description: args.description,
                paletteId: args.paletteId,
                typography: args.typography,
                spacing: args.spacing,
                borders: args.borders,
                cssOverrides: args.cssOverrides,
                layoutStyle: args.layoutStyle,
                isActive: args.isActive,
                isSystem: args.isSystem,
                updatedAt: Date.now(),
            });
            return existing._id;
        } else {
            const now = Date.now();
            return await ctx.db.insert("themeConfigs", {
                ...args,
                createdAt: now,
                updatedAt: now,
            });
        }
    },
});
