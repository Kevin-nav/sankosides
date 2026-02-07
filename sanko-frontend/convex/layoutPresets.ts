import { query, mutation } from "./_generated/server";
import { v } from "convex/values";

// Get all active layout presets
export const getActive = query({
    args: {},
    handler: async (ctx) => {
        return await ctx.db
            .query("layoutPresets")
            .withIndex("by_preset_id")
            .collect();
    },
});

// Get a specific layout preset by ID
export const getById = query({
    args: { presetId: v.string() },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("layoutPresets")
            .withIndex("by_preset_id", (q) => q.eq("presetId", args.presetId))
            .unique();
    },
});

// Upsert a layout preset (Migration safe)
export const upsert = mutation({
    args: {
        presetId: v.string(),
        name: v.string(),
        description: v.optional(v.string()),
        config: v.any(),
        isSystem: v.boolean(),
    },
    handler: async (ctx, args) => {
        const existing = await ctx.db
            .query("layoutPresets")
            .withIndex("by_preset_id", (q) => q.eq("presetId", args.presetId))
            .unique();

        if (existing) {
            // Update existing
            await ctx.db.patch(existing._id, {
                name: args.name,
                description: args.description,
                config: args.config,
                isSystem: args.isSystem,
                updatedAt: Date.now(),
            });
            return existing._id;
        } else {
            // Insert new
            const now = Date.now();
            return await ctx.db.insert("layoutPresets", {
                presetId: args.presetId,
                name: args.name,
                description: args.description,
                config: args.config,
                isSystem: args.isSystem,
                createdAt: now,
                updatedAt: now,
            });
        }
    },
});
