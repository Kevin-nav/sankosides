/**
 * Convex Hook for Generation Progress
 * 
 * Real-time subscription to AI slide generation progress.
 * UI updates automatically as backend pushes progress updates.
 */

import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";

// ===================================
// Types
// ===================================

export interface GenerationProgress {
    _id: Id<"generationProgress">;
    projectId: Id<"projects">;
    sessionId: string;
    currentStep: string;
    stepProgress: number;
    currentSlideIndex?: number;
    totalSlides?: number;
    message?: string;
    error?: string;
    createdAt: number;
    updatedAt: number;
}

// Step descriptions for UI display
export const GENERATION_STEPS: Record<string, { label: string; description: string }> = {
    initializing: { label: "Initializing", description: "Setting up generation..." },
    parsing: { label: "Parsing Content", description: "Analyzing your input..." },
    outlining: { label: "Creating Outline", description: "Structuring your presentation..." },
    generating: { label: "Generating Slides", description: "AI is creating your slides..." },
    rendering: { label: "Rendering", description: "Finalizing presentation..." },
    complete: { label: "Complete", description: "Your presentation is ready!" },
    error: { label: "Error", description: "Something went wrong" },
};

// ===================================
// Hooks
// ===================================

/**
 * Hook to subscribe to generation progress by project ID
 * Updates in real-time as backend pushes progress
 */
export function useGenerationProgress(projectId: Id<"projects"> | null | undefined) {
    return useQuery(
        api.generation.getProgressByProject,
        projectId ? { projectId } : "skip"
    ) as GenerationProgress | null | undefined;
}

/**
 * Hook to subscribe to generation progress by session ID
 */
export function useGenerationProgressBySession(sessionId: string | null | undefined) {
    return useQuery(
        api.generation.getProgressBySession,
        sessionId ? { sessionId } : "skip"
    ) as GenerationProgress | null | undefined;
}

/**
 * Get formatted progress information for UI display
 */
export function getProgressDisplay(progress: GenerationProgress | null | undefined) {
    if (!progress) {
        return {
            step: "idle",
            label: "Ready",
            description: "Waiting to start...",
            percentage: 0,
            slideInfo: null,
            isComplete: false,
            hasError: false,
        };
    }

    const stepInfo = GENERATION_STEPS[progress.currentStep] || {
        label: progress.currentStep,
        description: progress.message || "",
    };

    const slideInfo = progress.currentSlideIndex !== undefined && progress.totalSlides
        ? `Slide ${progress.currentSlideIndex + 1} of ${progress.totalSlides}`
        : null;

    return {
        step: progress.currentStep,
        label: stepInfo.label,
        description: progress.message || stepInfo.description,
        percentage: progress.stepProgress,
        slideInfo,
        isComplete: progress.currentStep === "complete",
        hasError: progress.currentStep === "error",
        errorMessage: progress.error,
    };
}
