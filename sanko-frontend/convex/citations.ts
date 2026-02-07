import { v } from "convex/values";
import { query, mutation } from "./_generated/server";

/**
 * Citation Cache Convex Functions
 * 
 * Replaces PostgreSQL tier in the 2-tier citation cache.
 * Redis remains as hot cache (handled in Python backend).
 */

// ===================================
// Queries
// ===================================

/**
 * Get cached citations by query hash.
 * Returns null if not found or expired.
 */
export const getCachedCitations = query({
    args: { queryHash: v.string() },
    handler: async (ctx, args) => {
        const cached = await ctx.db
            .query("cachedCitations")
            .withIndex("by_query_hash", (q) => q.eq("queryHash", args.queryHash))
            .first();

        if (!cached) {
            return null;
        }

        // Check if expired
        const now = Date.now();
        if (cached.expiresAt < now) {
            return null; // Expired
        }

        return cached;
    },
});

/**
 * Get multiple cached citations by query hashes (batch query).
 */
export const getCachedCitationsBatch = query({
    args: { queryHashes: v.array(v.string()) },
    handler: async (ctx, args) => {
        const now = Date.now();
        const results: Record<string, any> = {};

        for (const hash of args.queryHashes) {
            const cached = await ctx.db
                .query("cachedCitations")
                .withIndex("by_query_hash", (q) => q.eq("queryHash", hash))
                .first();

            if (cached && cached.expiresAt >= now) {
                results[hash] = cached;
            }
        }

        return results;
    },
});

// ===================================
// Mutations
// ===================================

/**
 * Store citation results in cache.
 * Updates existing entry or creates new one.
 */
export const storeCitations = mutation({
    args: {
        queryHash: v.string(),
        normalizedQuery: v.string(),
        citationData: v.any(), // Array of citation objects
        provider: v.string(),
        ttlHours: v.optional(v.number()), // Default 168 hours (7 days)
    },
    handler: async (ctx, args) => {
        const now = Date.now();
        const ttlMs = (args.ttlHours ?? 168) * 60 * 60 * 1000; // Default 7 days

        // Check if entry exists
        const existing = await ctx.db
            .query("cachedCitations")
            .withIndex("by_query_hash", (q) => q.eq("queryHash", args.queryHash))
            .first();

        if (existing) {
            // Update existing entry
            await ctx.db.patch(existing._id, {
                citationData: args.citationData,
                provider: args.provider,
                expiresAt: now + ttlMs,
            });
            return existing._id;
        }

        // Create new entry
        return await ctx.db.insert("cachedCitations", {
            queryHash: args.queryHash,
            normalizedQuery: args.normalizedQuery,
            citationData: args.citationData,
            provider: args.provider,
            createdAt: now,
            expiresAt: now + ttlMs,
        });
    },
});

/**
 * Delete expired citations (cleanup job).
 * Can be called periodically to clean up stale entries.
 */
export const cleanupExpiredCitations = mutation({
    args: {},
    handler: async (ctx) => {
        const now = Date.now();
        let deletedCount = 0;

        // Get all cached citations
        const allCached = await ctx.db.query("cachedCitations").collect();

        for (const cached of allCached) {
            if (cached.expiresAt < now) {
                await ctx.db.delete(cached._id);
                deletedCount++;
            }
        }

        return { deletedCount };
    },
});

/**
 * Get cache statistics.
 */
export const getCacheStats = query({
    args: {},
    handler: async (ctx) => {
        const now = Date.now();
        const allCached = await ctx.db.query("cachedCitations").collect();

        const total = allCached.length;
        const expired = allCached.filter((c) => c.expiresAt < now).length;
        const valid = total - expired;

        // Group by provider
        const byProvider: Record<string, number> = {};
        for (const cached of allCached) {
            if (cached.expiresAt >= now) {
                byProvider[cached.provider] = (byProvider[cached.provider] || 0) + 1;
            }
        }

        return {
            total,
            valid,
            expired,
            byProvider,
        };
    },
});
