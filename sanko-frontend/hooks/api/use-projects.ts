/**
 * Projects API Hooks
 * 
 * TanStack Query hooks for project CRUD operations.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/components/auth-provider";
import { queryKeys } from "./keys";

interface Project {
    id: string;
    title: string;
    mode: "replica" | "synthesis" | "research";
    description?: string;
    thumbnailUrl?: string;
    status: string;
    sessionId?: string;
    slidesData?: Record<string, unknown> | unknown[];
    createdAt: string;
    updatedAt: string;
}

interface CreateProjectInput {
    title: string;
    mode?: string;
    description?: string;
}

async function fetchProjects(token: string): Promise<Project[]> {
    const response = await fetch("/api/projects", {
        headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
        throw new Error("Failed to fetch projects");
    }

    const data = await response.json();
    return data.projects || [];
}

async function createProject(token: string, input: CreateProjectInput): Promise<{ project: Project }> {
    const response = await fetch("/api/projects", {
        method: "POST",
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
        },
        body: JSON.stringify(input),
    });

    if (!response.ok) {
        throw new Error("Failed to create project");
    }

    return response.json();
}

async function deleteProject(token: string, projectId: string): Promise<void> {
    const response = await fetch(`/api/projects/${projectId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
    });

    if (!response.ok) {
        throw new Error("Failed to delete project");
    }
}

/**
 * Hook to fetch all user projects
 */
export function useProjects() {
    const { user } = useAuth();

    return useQuery({
        queryKey: queryKeys.projects.all,
        queryFn: async () => {
            if (!user) throw new Error("Not authenticated");
            const token = await user.getIdToken();
            return fetchProjects(token);
        },
        enabled: !!user,
        staleTime: 30 * 1000, // 30 seconds
    });
}

/**
 * Hook to fetch a single project by ID
 */
export function useProject(projectId: string) {
    const { user } = useAuth();

    return useQuery({
        queryKey: queryKeys.projects.detail(projectId),
        queryFn: async () => {
            if (!user) throw new Error("Not authenticated");
            const token = await user.getIdToken();
            const response = await fetch(`/api/projects/${projectId}`, {
                headers: { Authorization: `Bearer ${token}` },
            });
            if (!response.ok) throw new Error("Failed to fetch project");
            return response.json();
        },
        enabled: !!user && !!projectId,
    });
}

/**
 * Hook to create a new project
 * Includes optimistic update
 */
export function useCreateProject() {
    const { user } = useAuth();
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (input: CreateProjectInput) => {
            if (!user) throw new Error("Not authenticated");
            const token = await user.getIdToken();
            return createProject(token, input);
        },
        onSuccess: (data) => {
            // Add new project to cache
            queryClient.setQueryData<Project[]>(queryKeys.projects.all, (old) => {
                return old ? [data.project, ...old] : [data.project];
            });
        },
        onError: () => {
            // Refetch to ensure consistency
            queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        },
    });
}

/**
 * Hook to delete a project
 * Includes optimistic update
 */
export function useDeleteProject() {
    const { user } = useAuth();
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (projectId: string) => {
            if (!user) throw new Error("Not authenticated");
            const token = await user.getIdToken();
            return deleteProject(token, projectId);
        },
        onMutate: async (projectId) => {
            // Cancel outgoing refetches
            await queryClient.cancelQueries({ queryKey: queryKeys.projects.all });

            // Snapshot previous value
            const previousProjects = queryClient.getQueryData<Project[]>(queryKeys.projects.all);

            // Optimistically remove from cache
            queryClient.setQueryData<Project[]>(queryKeys.projects.all, (old) => {
                return old?.filter((p) => p.id !== projectId) || [];
            });

            return { previousProjects };
        },
        onError: (_err, _projectId, context) => {
            // Rollback on error
            if (context?.previousProjects) {
                queryClient.setQueryData(queryKeys.projects.all, context.previousProjects);
            }
        },
        onSettled: () => {
            // Always refetch after mutation
            queryClient.invalidateQueries({ queryKey: queryKeys.projects.all });
        },
    });
}
