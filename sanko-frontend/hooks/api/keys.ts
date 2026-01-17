/**
 * Centralized Query Keys
 * 
 * All query keys in one place for easy cache invalidation
 * and type-safe query management.
 */

export const queryKeys = {
    // Projects
    projects: {
        all: ["projects"] as const,
        detail: (id: string) => ["projects", id] as const,
    },

    // Templates & Themes
    templates: {
        all: ["templates"] as const,
        byCategory: (category: string) => ["templates", category] as const,
    },
    themes: {
        all: ["themes"] as const,
    },
    palettes: {
        all: ["palettes"] as const,
    },

    // Universities
    universities: {
        hierarchy: ["universities", "hierarchy"] as const,
    },

    // User
    user: {
        profile: ["user", "profile"] as const,
        preferences: ["user", "preferences"] as const,
    },

    // Generation Sessions
    generation: {
        session: (id: string) => ["generation", "session", id] as const,
        status: (id: string) => ["generation", "status", id] as const,
        slides: (id: string) => ["generation", "slides", id] as const,
    },
};
