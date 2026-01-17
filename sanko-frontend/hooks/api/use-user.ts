/**
 * User & Universities API Hooks
 * 
 * TanStack Query hooks for user profile and university hierarchy.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/components/auth-provider";
import { queryKeys } from "./keys";

// Types
interface DepartmentHierarchy {
    department_id: string;
    name: string;
    is_stem: boolean;
}

interface FacultyHierarchy {
    faculty_id: string;
    name: string;
    short_name: string;
    departments: DepartmentHierarchy[];
}

interface UniversityHierarchy {
    university_id: string;
    name: string;
    short_name: string;
    country: string;
    default_citation_style: string;
    spelling_variant: string;
    unit_system: string;
    faculties: FacultyHierarchy[];
}

interface HierarchyResponse {
    universities: UniversityHierarchy[];
    cached: boolean;
    cache_ttl_seconds: number;
}

interface ProfileUpdateInput {
    displayName?: string;
    universityId?: string | null;
    facultyId?: string | null;
    departmentId?: string | null;
    academicLevel?: string | null;
    academicYear?: number | null;
}

interface PreferencesUpdateInput {
    theme?: string;
    citationStyle?: string;
    language?: string;
    marketingEmails?: boolean;
}

/**
 * Hook to fetch university hierarchy
 * 1 hour cache - this data is very static
 */
export function useUniversities() {
    return useQuery({
        queryKey: queryKeys.universities.hierarchy,
        queryFn: async () => {
            const response = await fetch("/api/universities");
            if (!response.ok) {
                throw new Error("Failed to fetch universities");
            }
            return response.json() as Promise<HierarchyResponse>;
        },
        staleTime: 60 * 60 * 1000, // 1 hour
        gcTime: 2 * 60 * 60 * 1000, // 2 hours
    });
}

/**
 * Hook to update user profile
 */
export function useUpdateProfile() {
    const { user, syncUser } = useAuth();
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (input: ProfileUpdateInput) => {
            if (!user) throw new Error("Not authenticated");
            const token = await user.getIdToken();

            const response = await fetch("/api/user/profile", {
                method: "PUT",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(input),
            });

            if (!response.ok) {
                throw new Error("Failed to update profile");
            }

            return response.json();
        },
        onSuccess: async () => {
            // Sync the user in auth context
            await syncUser();
            // Invalidate user queries
            queryClient.invalidateQueries({ queryKey: queryKeys.user.profile });
        },
    });
}

/**
 * Hook to update user preferences
 */
export function useUpdatePreferences() {
    const { user } = useAuth();
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (input: PreferencesUpdateInput) => {
            if (!user) throw new Error("Not authenticated");
            const token = await user.getIdToken();

            const response = await fetch("/api/user/preferences", {
                method: "PUT",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify(input),
            });

            if (!response.ok) {
                throw new Error("Failed to update preferences");
            }

            return response.json();
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.user.preferences });
        },
    });
}

// Re-export types
export type {
    UniversityHierarchy,
    FacultyHierarchy,
    DepartmentHierarchy,
    HierarchyResponse,
    ProfileUpdateInput,
    PreferencesUpdateInput,
};
