/**
 * Convex Hooks for Project Management
 * 
 * Direct Convex queries/mutations for project data.
 * Real-time updates - UI refreshes automatically when projects change.
 */

import { useQuery, useMutation } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";

// ===================================
// Types
// ===================================

export interface Project {
    _id: Id<"projects">;
    userId: Id<"users">;
    title: string;
    description?: string;
    thumbnailUrl?: string;
    status: string; // 'draft' | 'generating' | 'completed'
    sessionId?: string;
    slidesData?: unknown;
    createdAt: number;
    updatedAt: number;
}

// ===================================
// Queries - Real-time subscriptions
// ===================================

/**
 * Hook to get a single project by ID
 * Real-time subscription - updates when project changes
 */
export function useProject(projectId: Id<"projects"> | null | undefined) {
    return useQuery(
        api.projects.get,
        projectId ? { id: projectId } : "skip"
    );
}

/**
 * Hook to get all projects for a user
 * Re-exported from use-user.ts for convenience
 */
export { useUserProjects } from "./use-user";

// ===================================
// Mutations
// ===================================

/**
 * Hook to create a new project
 */
export function useCreateProject() {
    return useMutation(api.projects.create);
}

/**
 * Hook to update a project
 * Used for updating title, status, slides data, etc.
 */
export function useUpdateProject() {
    return useMutation(api.projects.update);
}

/**
 * Hook to delete a project
 */
export function useDeleteProject() {
    return useMutation(api.projects.deleteProject);
}

// ===================================
// Compound Hooks (for common patterns)
// ===================================

/**
 * Hook that provides all project CRUD operations
 * Convenient for components that need multiple operations
 */
export function useProjectOperations() {
    const createProject = useCreateProject();
    const updateProject = useUpdateProject();
    const deleteProject = useDeleteProject();

    return {
        createProject,
        updateProject,
        deleteProject,
    };
}
