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
            .withIndex("by_user_updated_at", (q) => q.eq("userId", args.userId))
            .order("desc")
            .collect();
    }
});

// Update user preferences
export const updatePreferences = mutation({
    args: {
        firebaseUid: v.string(),
        preferences: v.any(),
    },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_firebase_uid", (q) => q.eq("firebaseUid", args.firebaseUid))
            .first();

        if (!user) {
            throw new Error("User not found");
        }

        await ctx.db.patch(user._id, {
            preferences: args.preferences,
            updatedAt: Date.now(),
        });
    },
});

// Update university profile
export const updateUniversityProfile = mutation({
    args: {
        firebaseUid: v.string(),
        universityProfile: v.any(),
    },
    handler: async (ctx, args) => {
        const user = await ctx.db
            .query("users")
            .withIndex("by_firebase_uid", (q) => q.eq("firebaseUid", args.firebaseUid))
            .first();

        if (!user) {
            throw new Error("User not found");
        }

        await ctx.db.patch(user._id, {
            universityProfile: args.universityProfile,
            updatedAt: Date.now(),
        });
    },
});

