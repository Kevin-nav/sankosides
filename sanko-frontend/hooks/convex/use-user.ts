/**
 * Convex Hooks for User Management
 * 
 * Direct Convex queries/mutations for user data - replaces Neon API calls.
 * Real-time updates via WebSocket subscriptions.
 */

import { useQuery, useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";

// ===================================
// Types
// ===================================

export interface ConvexUser {
    _id: Id<"users">;
    firebaseUid: string;
    email: string;
    displayName?: string;
    photoUrl?: string;
    universityProfile?: Record<string, unknown>;
    preferences?: Record<string, unknown>;
    subscriptionTier?: string;
    createdAt: number;
    updatedAt: number;
}

// ===================================
// Queries - Real-time subscriptions
// ===================================

/**
 * Hook to get current user by Firebase UID
 * Automatically updates when user data changes
 */
export function useUser(firebaseUid: string | null | undefined) {
    return useQuery(
        api.users.getUser,
        firebaseUid ? { firebaseUid } : "skip"
    );
}

/**
 * Hook to get all projects for a user
 * Real-time subscription - updates instantly when projects change
 */
export function useUserProjects(userId: Id<"users"> | null | undefined) {
    return useQuery(
        api.users.getProjects,
        userId ? { userId } : "skip"
    );
}

// ===================================
// Mutations
// ===================================

/**
 * Hook to sync user data from Firebase to Convex
 * Call this after Firebase authentication
 */
export function useSyncUser() {
    return useMutation(api.users.syncUser);
}

/**
 * Hook to update user preferences
 */
export function useUpdateUserPreferences() {
    return useMutation(api.users.updatePreferences);
}

/**
 * Hook to update university profile
 */
export function useUpdateUniversityProfile() {
    return useMutation(api.users.updateUniversityProfile);
}
