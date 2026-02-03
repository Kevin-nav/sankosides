import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const syncUser = mutation({
    args: {
        firebaseUid: v.string(),
        email: v.string(),
        displayName: v.optional(v.string()),
        photoUrl: v.optional(v.string()),
    },
    handler: async (ctx, args) => {
        const existingUser = await ctx.db
            .query("users")
            .withIndex("by_firebase_uid", (q) => q.eq("firebaseUid", args.firebaseUid))
            .first();

        const now = Date.now();

        if (existingUser) {
            await ctx.db.patch(existingUser._id, {
                email: args.email,
                displayName: args.displayName,
                photoUrl: args.photoUrl,
                updatedAt: now,
            });
            return existingUser._id;
        }

        const newUserId = await ctx.db.insert("users", {
            firebaseUid: args.firebaseUid,
            email: args.email,
            displayName: args.displayName,
            photoUrl: args.photoUrl,
            subscriptionTier: "free",
            createdAt: now,
            updatedAt: now,
        });
        return newUserId;
    },
});

export const getUser = query({
    args: { firebaseUid: v.string() },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("users")
            .withIndex("by_firebase_uid", (q) => q.eq("firebaseUid", args.firebaseUid))
            .first();
    },
});

export const getProjects = query({
    args: { userId: v.id("users") },
    handler: async (ctx, args) => {
        return await ctx.db
            .query("projects")
            .withIndex("by_user_id", (q) => q.eq("userId", args.userId))
            .order("desc")
            .collect();
    }
});
