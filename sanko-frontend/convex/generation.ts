/**
 * Convex Mutations and Queries for Generation Progress
 * 
 * Enables real-time tracking of AI slide generation.
 * Backend pushes updates via HTTP mutations, frontend subscribes via queries.
 * 
 * All generation sessions MUST have a valid projectId for tracking.
 */

import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

// ===================================
// Mutations - Called by Python backend
// ===================================

/**
 * Start tracking a new generation session
 */
export const startGeneration = mutation({
    args: {
        projectId: v.id("projects"),
        sessionId: v.string(),
    },
    handler: async (ctx, args) => {
        const now = Date.now();

        // Check if progress already exists for this session
        const existing = await ctx.db
            .query("generationProgress")
            .withIndex("by_session_id", (q) => q.eq("sessionId", args.sessionId))
            .first();

        if (existing) {
            // Update existing record
            await ctx.db.patch(existing._id, {
                currentStep: "initializing",
                stepProgress: 0,
                message: "Starting generation...",
                error: undefined,
                updatedAt: now,
            });
            return existing._id;
        }

        // Create new progress record
        const progressId = await ctx.db.insert("generationProgress", {
            projectId: args.projectId,
            sessionId: args.sessionId,
            currentStep: "initializing",
            stepProgress: 0,
            message: "Starting generation...",
            createdAt: now,
            updatedAt: now,
        });

        // Update project status
        await ctx.db.patch(args.projectId, {
            status: "generating",
            sessionId: args.sessionId,
            updatedAt: now,
        });

        return progressId;
    },
});

/**
 * Update generation progress (called by backend at each step)
 */
export const updateProgress = mutation({
    args: {
        sessionId: v.string(),
        currentStep: v.string(),
        stepProgress: v.number(),
        currentSlideIndex: v.optional(v.number()),
        totalSlides: v.optional(v.number()),
        message: v.optional(v.string()),
        blueprint: v.optional(v.any()),
        clarificationStatus: v.optional(v.string()),
    },
    handler: async (ctx, args) => {
        const progress = await ctx.db
            .query("generationProgress")
            .withIndex("by_session_id", (q) => q.eq("sessionId", args.sessionId))
            .first();

        if (!progress) {
            throw new Error(`No generation progress found for session: ${args.sessionId}`);
        }

        const patch: any = {
            currentStep: args.currentStep,
            stepProgress: args.stepProgress,
            updatedAt: Date.now(),
        };

        if (args.currentSlideIndex !== undefined) patch.currentSlideIndex = args.currentSlideIndex;
        if (args.totalSlides !== undefined) patch.totalSlides = args.totalSlides;
        if (args.message !== undefined) patch.message = args.message;
        if (args.blueprint !== undefined) patch.blueprint = args.blueprint;
        if (args.clarificationStatus !== undefined) patch.clarificationStatus = args.clarificationStatus;

        await ctx.db.patch(progress._id, patch);
    },
});

/**
 * Mark generation as complete
 */
export const completeGeneration = mutation({
    args: {
        sessionId: v.string(),
        slidesData: v.optional(v.any()),
    },
    handler: async (ctx, args) => {
        const now = Date.now();

        const progress = await ctx.db
            .query("generationProgress")
            .withIndex("by_session_id", (q) => q.eq("sessionId", args.sessionId))
            .first();

        if (!progress) {
            throw new Error(`No generation progress found for session: ${args.sessionId}`);
        }

        // Update progress to complete
        await ctx.db.patch(progress._id, {
            currentStep: "complete",
            stepProgress: 100,
            message: "Generation complete!",
            updatedAt: now,
        });

        // Update project status and save slides
        await ctx.db.patch(progress.projectId, {
            status: "completed",
            slidesData: args.slidesData,
            updatedAt: now,
        });
    },
});

/**
 * Mark generation as failed
 */
export const failGeneration = mutation({
    args: {
        sessionId: v.string(),
        error: v.string(),
    },
    handler: async (ctx, args) => {
        const now = Date.now();

        const progress = await ctx.db
            .query("generationProgress")
            .withIndex("by_session_id", (q) => q.eq("sessionId", args.sessionId))
            .first();

        if (!progress) {
            throw new Error(`No generation progress found for session: ${args.sessionId}`);
        }

        // Update progress with error
        await ctx.db.patch(progress._id, {
            currentStep: "error",
            error: args.error,
            message: "Generation failed",
            updatedAt: now,
        });

        // Update project status
        await ctx.db.patch(progress.projectId, {
            status: "draft",
            updatedAt: now,
        });
    },
});

// ===================================
// Queries - Subscribed by Frontend
// ===================================

/**
 * Get generation progress by project ID (real-time subscription)
 */
export const getProgressByProject = query({
    args: { projectId: v.id("projects") },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("generationProgress")
            .withIndex("by_project_id", (q) => q.eq("projectId", args.projectId))
            .order("desc")
            .first();
    },
});

/**
 * Get generation progress by session ID
 */
export const getProgressBySession = query({
    args: { sessionId: v.string() },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("generationProgress")
            .withIndex("by_session_id", (q) => q.eq("sessionId", args.sessionId))
            .first();
    },
});
