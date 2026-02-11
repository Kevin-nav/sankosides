/**
 * Templates & Themes API Hooks
 * 
 * TanStack Query hooks for templates, themes, and palettes.
 * These are relatively static data, so we use longer cache times.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "./keys";
import { api } from "@/lib/api-client";

// Types (matching lib/templates.ts)
export interface Template {
    id: string;
    template_id: string;
    name: string;
    description: string;
    content_type: string;
    category: string;
    html_template: string;
    css_styles: string;
    version: string;
}

export interface Palette {
    id: string;
    name: string;
    category: string;
    colors: Record<string, string>;
    is_default: boolean;
}

export interface Theme {
    id: string;
    theme_id: string;
    name: string;
    description: string;
    palette: Palette;
    typography: Record<string, unknown>;
    spacing: Record<string, unknown>;
    borders: Record<string, unknown>;
}

/**
 * Hook to fetch all templates
 * 10 minute cache - templates rarely change
 */
export function useTemplates(category?: string) {
    return useQuery({
        queryKey: category ? queryKeys.templates.byCategory(category) : queryKeys.templates.all,
        queryFn: async () => {
            let url = "/api/templates";
            if (category && category !== "All") {
                url += `?category=${category.toLowerCase()}`;
            }
            return api.get<Template[]>(url);
        },
        staleTime: 10 * 60 * 1000, // 10 minutes
        gcTime: 30 * 60 * 1000, // 30 minutes
    });
}

/**
 * Hook to fetch all themes
 * 10 minute cache - themes rarely change
 */
export function useThemes() {
    return useQuery({
        queryKey: queryKeys.themes.all,
        queryFn: async () => api.get<Theme[]>("/api/themes"),
        staleTime: 10 * 60 * 1000, // 10 minutes
        gcTime: 30 * 60 * 1000, // 30 minutes
    });
}

/**
 * Hook to fetch all palettes
 * 10 minute cache - palettes rarely change
 */
export function usePalettes() {
    return useQuery({
        queryKey: queryKeys.palettes.all,
        queryFn: async () => api.get<Palette[]>("/api/palettes"),
        staleTime: 10 * 60 * 1000, // 10 minutes
        gcTime: 30 * 60 * 1000, // 30 minutes
    });
}

/**
 * Hook to create a new palette
 */
export function useCreatePalette() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (data: { name: string; category: string; colors: Record<string, string> }) => {
            return api.post<Palette>("/api/palettes", data);
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.palettes.all });
        },
    });
}

/**
 * Hook to update a palette
 */
export function useUpdatePalette() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({ id, ...data }: { id: string; name?: string; category?: string; colors?: Record<string, string> }) => {
            return api.request<Palette>(`/api/palettes/${id}`, {
                method: "PUT",
                body: JSON.stringify(data),
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.palettes.all });
            queryClient.invalidateQueries({ queryKey: queryKeys.themes.all });
        },
    });
}

/**
 * Hook to delete a palette
 */
export function useDeletePalette() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (id: string) => {
            return api.request<{ status: string }>(`/api/palettes/${id}`, {
                method: "DELETE",
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: queryKeys.palettes.all });
        },
    });
}

/**
 * Helper to get preview URL (not a hook, just re-export for convenience)
 */
export function getPreviewUrl(themeId: string, templateType: string = "title"): string {
    const baseUrl = api.getBaseUrl();
    return `${baseUrl}/api/themes/${themeId}/preview?template_type=${templateType}`;
}

/**
 * Hook to fetch template preview HTML
 * Used for eager loading/prefetching
 */
export function useTemplatePreview(themeId: string | null, templateType: string = "title") {
    return useQuery({
        queryKey: ["template-preview", themeId, templateType],
        queryFn: async () => {
            if (!themeId) return "";
            const url = getPreviewUrl(themeId, templateType);
            const res = await fetch(url);
            if (!res.ok) throw new Error("Failed to load preview");
            return res.text();
        },
        enabled: !!themeId,
        staleTime: 5 * 60 * 1000, // 5 minutes
    });
}
