/**
 * Generation Runs (Run History / Persistence)
 *
 * A "run" represents one attempt/session for a project (maps to python backend sessionId).
 * This allows resumability and history without overloading projects.sessionId.
 */

import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

const ALLOWED_STAGES = new Set(["clarifying", "blueprint", "generating", "completed", "failed"]);

function normalizeStage(stage: string | undefined): string {
    const s = (stage ?? "").trim().toLowerCase();
    if (ALLOWED_STAGES.has(s)) return s;
    // Keep it permissive so UI can evolve without schema churn; still normalize blanks.
    return s || "clarifying";
}

export const create = mutation({
    args: {
        projectId: v.id("projects"),
        sessionId: v.string(),
        mode: v.optional(v.string()),
        stage: v.optional(v.string()),
        brief: v.optional(v.any()),
        uploads: v.optional(v.any()),
    },
    handler: async (ctx, args) => {
        const now = Date.now();

        // Idempotency: if a run for sessionId already exists, return it.
        const existing = await ctx.db
            .query("generationRuns")
            .withIndex("by_session_id", (q) => q.eq("sessionId", args.sessionId))
            .first();
        if (existing) return existing._id;

        const runId = await ctx.db.insert("generationRuns", {
            projectId: args.projectId,
            sessionId: args.sessionId,
            mode: args.mode,
            stage: normalizeStage(args.stage),
            status: "active",
            brief: args.brief,
            uploads: args.uploads,
            createdAt: now,
            updatedAt: now,
        });

        return runId;
    },
});

export const update = mutation({
    args: {
        id: v.id("generationRuns"),
        stage: v.optional(v.string()),
        status: v.optional(v.string()),
        brief: v.optional(v.any()),
        uploads: v.optional(v.any()),
        scope: v.optional(v.any()),
        outline: v.optional(v.any()),
        result: v.optional(v.any()),
        error: v.optional(v.string()),
    },
    handler: async (ctx, args) => {
        const { id, ...updates } = args;
        const patch: Record<string, unknown> = { updatedAt: Date.now() };

        if (updates.stage !== undefined) patch.stage = normalizeStage(updates.stage);
        if (updates.status !== undefined) patch.status = updates.status;
        if (updates.brief !== undefined) patch.brief = updates.brief;
        if (updates.uploads !== undefined) patch.uploads = updates.uploads;
        if (updates.scope !== undefined) patch.scope = updates.scope;
        if (updates.outline !== undefined) patch.outline = updates.outline;
        if (updates.result !== undefined) patch.result = updates.result;
        if (updates.error !== undefined) patch.error = updates.error;

        await ctx.db.patch(id, patch);
    },
});

export const get = query({
    args: { id: v.id("generationRuns") },
    handler: async (ctx, args) => {
        return await ctx.db.get(args.id);
    },
});

export const getBySession = query({
    args: { sessionId: v.string() },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("generationRuns")
            .withIndex("by_session_id", (q) => q.eq("sessionId", args.sessionId))
            .first();
    },
});

export const listByProject = query({
    args: { projectId: v.id("projects") },
    handler: async (ctx, args) => {
        // No createdAt index; query by projectId then sort in memory.
        const runs = await ctx.db
            .query("generationRuns")
            .withIndex("by_project_id", (q) => q.eq("projectId", args.projectId))
            .collect();

        return runs.sort((a, b) => (b.createdAt ?? 0) - (a.createdAt ?? 0));
    },
});

