import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

const FALLBACK_TITLE = "Untitled Presentation";
const MAX_TITLE_LENGTH = 120;
const ALLOWED_STATUSES = new Set(["draft", "generating", "completed", "archived"]);
const ALLOWED_RESTORE_STATUSES = new Set(["draft", "generating", "completed"]);

function sanitizeTitle(rawTitle: string | undefined): string {
    const normalized = (rawTitle ?? "").replace(/\s+/g, " ").trim();
    if (!normalized) return FALLBACK_TITLE;
    return normalized.slice(0, MAX_TITLE_LENGTH);
}

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
            title: sanitizeTitle(args.title),
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
        archiveSourceStatus: v.optional(v.string()),
        clearArchiveSourceStatus: v.optional(v.boolean()),
        thumbnailUrl: v.optional(v.string()),
        slidesData: v.optional(v.any()),
        sessionId: v.optional(v.string()),
        activeRunId: v.optional(v.id("generationRuns")),
        clearActiveRunId: v.optional(v.boolean()),
    },
    handler: async (ctx, args) => {
        const { id, ...updates } = args;

        const patch: Record<string, unknown> = {
            updatedAt: Date.now(),
        };

        if (updates.description !== undefined) {
            patch.description = updates.description;
        }

        if (updates.thumbnailUrl !== undefined) {
            patch.thumbnailUrl = updates.thumbnailUrl;
        }

        if (updates.slidesData !== undefined) {
            patch.slidesData = updates.slidesData;
        }

        if (updates.sessionId !== undefined) {
            patch.sessionId = updates.sessionId;
        }

        if (updates.activeRunId !== undefined) {
            patch.activeRunId = updates.activeRunId;
        }
        if (updates.clearActiveRunId) {
            patch.activeRunId = undefined;
        }

        if (updates.title !== undefined) {
            patch.title = sanitizeTitle(updates.title);
        }

        if (updates.status !== undefined && !ALLOWED_STATUSES.has(updates.status)) {
            throw new Error(`Invalid project status: ${updates.status}`);
        }
        if (updates.status !== undefined) {
            patch.status = updates.status;
        }

        if (
            updates.archiveSourceStatus !== undefined &&
            !ALLOWED_RESTORE_STATUSES.has(updates.archiveSourceStatus)
        ) {
            throw new Error(`Invalid archive source status: ${updates.archiveSourceStatus}`);
        }
        if (updates.archiveSourceStatus !== undefined) {
            patch.archiveSourceStatus = updates.archiveSourceStatus;
        }

        if (updates.clearArchiveSourceStatus) {
            patch.archiveSourceStatus = undefined;
        }

        await ctx.db.patch(id, {
            ...patch,
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
