import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

// Create a new project
export const create = mutation({
    args: {
        title: v.string(),
        description: v.optional(v.string()),
        userId: v.id("users"),
    },
    handler: async (ctx, args) => {
        const now = Date.now();
        const projectId = await ctx.db.insert("projects", {
            userId: args.userId,
            title: args.title,
            description: args.description,
            status: "draft",
            createdAt: now,
            updatedAt: now,
        });
        return projectId;
    },
});

// Update project status or content (used by Python backend mostly)
export const update = mutation({
    args: {
        id: v.id("projects"),
        title: v.optional(v.string()),
        description: v.optional(v.string()),
        status: v.optional(v.string()),
        thumbnailUrl: v.optional(v.string()),
        slidesData: v.optional(v.any()),
        sessionId: v.optional(v.string()),
    },
    handler: async (ctx, args) => {
        const { id, ...updates } = args;
        await ctx.db.patch(id, {
            ...updates,
            updatedAt: Date.now(),
        });
    },
});

// Get single project
export const get = query({
    args: { id: v.id("projects") },
    handler: async (ctx, args) => {
        return await ctx.db.get(args.id);
    },
});

// Delete project
export const deleteProject = mutation({
    args: { id: v.id("projects") },
    handler: async (ctx, args) => {
        await ctx.db.delete(args.id);
    },
});
