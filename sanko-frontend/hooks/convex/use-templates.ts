/**
 * Convex Hooks for Templates, Themes, and Palettes
 * 
 * Direct Convex queries - no backend API round-trip needed.
 * These replace the API-based hooks for simple data fetching.
 */

import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";

// ===================================
// Types (matching backend schemas)
// ===================================

export interface Template {
    _id: string;
    templateId: string;
    name: string;
    description?: string;
    contentType: string;
    category: string;
    htmlTemplate: string;
    cssStyles?: string;
    version: string;
    isActive: boolean;
    isSystem: boolean;
}

export interface Palette {
    _id: string;
    name: string;
    category: string;
    colors: Record<string, string>;
    isDefault: boolean;
    isSystem: boolean;
}

export interface Theme {
    _id: string;
    themeId: string;
    name: string;
    description?: string;
    palette?: Palette | null;
    typography?: Record<string, string>;
    spacing?: Record<string, string>;
    borders?: Record<string, string>;
    cssOverrides?: string;
    layoutStyle?: string;
    isActive: boolean;
    isSystem: boolean;
}

// ===================================
// Hooks - Direct Convex Queries
// ===================================

/**
 * Hook to fetch all templates directly from Convex
 * 
 * No staleTime needed - Convex handles real-time updates automatically
 */
export function useTemplates(category?: string) {
    return useQuery(api.templates.listTemplates,
        category ? { category } : {}
    );
}

/**
 * Hook to fetch a single template by ID
 */
export function useTemplate(templateId: string | null) {
    return useQuery(
        api.templates.getTemplateFn,
        templateId ? { templateId } : "skip"
    );
}

/**
 * Hook to fetch all themes with their palettes
 */
export function useThemes() {
    return useQuery(api.templates.listThemes);
}

/**
 * Hook to fetch a single theme by ID
 */
export function useTheme(themeId: string | null) {
    return useQuery(
        api.templates.getThemeFn,
        themeId ? { themeId } : "skip"
    );
}

/**
 * Hook to fetch all palettes
 */
export function usePalettes() {
    return useQuery(api.templates.listPalettes);
}

// ===================================
// Helpers
// ===================================

/**
 * Get preview URL for a theme (still uses backend for rendering)
 * 
 * Preview rendering involves Jinja2 templates and is kept in backend
 */
export function getPreviewUrl(themeId: string, templateType: string = "title"): string {
    const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    return `${baseUrl}/api/themes/${themeId}/preview?template_type=${templateType}`;
}
