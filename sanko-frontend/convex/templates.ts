import { v } from "convex/values";
import { query, mutation } from "./_generated/server";

// ===================================
// Slide Templates
// ===================================

export const getTemplateFn = query({
    args: { templateId: v.string() },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("templates")
            .withIndex("by_template_id", (q) => q.eq("templateId", args.templateId))
            .first();
    },
});

export const listTemplates = query({
    args: { category: v.optional(v.string()) },
    handler: async (ctx, args) => {
        let q = ctx.db.query("templates");
        if (args.category) {
            q = q.withIndex("by_category", (q) => q.eq("category", args.category!));
        }
        return await q.collect();
    },
});

// Admin/System tool to seed templates
export const createTemplate = mutation({
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
        const exists = await ctx.db
            .query("templates")
            .withIndex("by_template_id", (q) => q.eq("templateId", args.templateId))
            .first();

        const now = Date.now();
        if (exists) {
            return await ctx.db.patch(exists._id, {
                ...args,
                updatedAt: now,
            });
        }

        return await ctx.db.insert("templates", {
            ...args,
            createdAt: now,
            updatedAt: now,
        });
    },
});

// ===================================
// Themes
// ===================================

export const getThemeFn = query({
    args: { themeId: v.string() },
    handler: async (ctx, args) => {
        const theme = await ctx.db
            .query("themeConfigs")
            .withIndex("by_theme_id", (q) => q.eq("themeId", args.themeId))
            .first();

        if (!theme) return null;

        // Join with palette
        let palette = null;
        if (theme.paletteId) {
            palette = await ctx.db.get(theme.paletteId);
        }

        return {
            ...theme,
            palette,
        };
    }
});

export const listThemes = query({
    handler: async (ctx) => {
        return await ctx.db.query("themeConfigs").collect();
    }
});
