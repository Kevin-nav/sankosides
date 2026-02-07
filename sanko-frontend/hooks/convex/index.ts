/**
 * Convex Hooks
 * 
 * Direct Convex queries - no backend API round-trip needed.
 * Use these instead of API hooks for simple data fetching.
 * 
 * For API-based hooks (backend-critical operations like AI generation),
 * continue using hooks/api/*.
 */

// Re-export Id type for convenience
export type { Id } from "@/convex/_generated/dataModel";

// Template, Theme, and Palette hooks
export {
    useTemplates,
    useTemplate,
    useThemes,
    useTheme,
    usePalettes,
    getPreviewUrl,
    type Template,
    type Theme,
    type Palette,
} from "./use-templates";

// University hierarchy hooks
export {
    useUniversityHierarchy,
    useUniversities,
    useUniversity,
    useFaculties,
    useDepartments,
    type University,
    type Faculty,
    type Department,
} from "./use-universities";

// User hooks
export {
    useUser,
    useUserProjects,
    useSyncUser,
    useUpdateUserPreferences,
    useUpdateUniversityProfile,
    type ConvexUser,
} from "./use-user";

// Project hooks
export {
    useProject,
    useCreateProject,
    useUpdateProject,
    useDeleteProject,
    useProjectOperations,
    type Project,
} from "./use-projects";

// Generation progress hooks
export {
    useGenerationProgress,
    useGenerationProgressBySession,
    getProgressDisplay,
    GENERATION_STEPS,
    type GenerationProgress,
} from "./use-generation";


