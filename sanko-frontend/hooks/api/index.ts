/**
 * API Hooks - Barrel Export
 * 
 * Import all hooks from this file for cleaner imports.
 */

// Query Keys
export { queryKeys } from "./keys";

// Projects
export {
    useProjects,
    useProject,
    useCreateProject,
    useDeleteProject,
} from "./use-projects";

// Templates & Themes
export {
    useTemplates,
    useThemes,
    usePalettes,
    useCreatePalette,
    useUpdatePalette,
    useDeletePalette,
    getPreviewUrl,
    useTemplatePreview,
} from "./use-templates";
export type { Template, Theme, Palette } from "./use-templates";

// User & Universities
export {
    useUniversities,
    useUpdateProfile,
    useUpdatePreferences,
} from "./use-user";
export type {
    UniversityHierarchy,
    FacultyHierarchy,
    DepartmentHierarchy,
    HierarchyResponse,
    ProfileUpdateInput,
    PreferencesUpdateInput,
} from "./use-user";

// Generation Sessions
export {
    useSessionStatus,
    useStartSession,
    useClarify,
    useApproveOutline,
    useGeneratedSlides,
    useTriggerGeneration,
} from "./use-generation";
export type {
    SessionStatus,
    ClarifyRequest,
    ClarifyResponse,
    StartSessionResponse,
} from "./use-generation";
