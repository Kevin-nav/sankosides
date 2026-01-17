/**
 * Generation Session API Hooks
 * 
 * TanStack Query hooks for AI generation sessions.
 * Uses polling for reliable progress updates.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "./keys";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

// Types
export interface SessionStatus {
    session_id: string;
    status: "active" | "clarifying" | "outlining" | "generating" | "completed" | "failed";
    current_stage: string;
    slides_completed: number;
    total_slides: number;
    order_form?: Record<string, any>;
    skeleton?: Record<string, any>;
    generated_slides?: any[];
    qa_score?: number;
    error?: string;
}

export interface ClarifyRequest {
    message: string;
    file_hashes?: string[];
}

export interface ClarifyResponse {
    session_id: string;
    complete: boolean;
    question?: string;
    order_form?: Record<string, any>;
    needs_confirmation: boolean;
    summary?: Record<string, any>;
    message?: string;
}

export interface StartSessionResponse {
    session_id: string;
    status: string;
    message: string;
    files_uploaded?: number;
    cache_hits?: number;
}

/**
 * Hook to poll session status
 * Used as reliable alternative/complement to SSE
 */
export function useSessionStatus(
    sessionId: string | null,
    options?: {
        enabled?: boolean;
        refetchInterval?: number | false;
    }
) {
    const isGenerating = options?.enabled !== false;

    return useQuery({
        queryKey: queryKeys.generation.status(sessionId || ""),
        queryFn: async () => {
            const response = await fetch(`/api/generate/status/${sessionId}`);
            if (!response.ok) {
                throw new Error("Failed to fetch session status");
            }
            return response.json() as Promise<SessionStatus>;
        },
        enabled: !!sessionId && isGenerating,
        // Poll every 2 seconds during generation
        refetchInterval: options?.refetchInterval ?? (isGenerating ? 2000 : false),
        // Stop polling when complete
        refetchIntervalInBackground: false,
    });
}

/**
 * Hook to start a new generation session
 */
export function useStartSession() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (files?: File[]) => {
            const formData = new FormData();
            if (files) {
                files.forEach((file) => formData.append("files", file));
            }

            const response = await fetch("/api/generate/start", {
                method: "POST",
                body: files ? formData : undefined,
            });

            if (!response.ok) {
                throw new Error("Failed to start session");
            }

            return response.json() as Promise<StartSessionResponse>;
        },
        onSuccess: (data) => {
            // Prefetch the session status
            queryClient.prefetchQuery({
                queryKey: queryKeys.generation.status(data.session_id),
                queryFn: async () => {
                    const response = await fetch(`/api/generate/status/${data.session_id}`);
                    return response.json();
                },
            });
        },
    });
}

/**
 * Hook to send clarification message
 */
export function useClarify(sessionId: string | null) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (input: ClarifyRequest) => {
            const response = await fetch(`/api/generate/clarify/${sessionId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(input),
            });

            if (!response.ok) {
                throw new Error("Failed to send clarification");
            }

            return response.json() as Promise<ClarifyResponse>;
        },
        onSuccess: () => {
            // Invalidate session status to get fresh data
            if (sessionId) {
                queryClient.invalidateQueries({
                    queryKey: queryKeys.generation.status(sessionId),
                });
            }
        },
    });
}

/**
 * Hook to approve outline and start generation
 */
export function useApproveOutline(sessionId: string | null) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async (modifications?: { modified_skeleton?: any }) => {
            const response = await fetch(`/api/generate/blueprint/${sessionId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(modifications || {}),
            });

            if (!response.ok) {
                throw new Error("Failed to approve outline");
            }

            return response.json();
        },
        onSuccess: () => {
            // Invalidate session status to start polling generation progress
            if (sessionId) {
                queryClient.invalidateQueries({
                    queryKey: queryKeys.generation.status(sessionId),
                });
            }
        },
    });
}

/**
 * Hook to fetch generated slides
 */
export function useGeneratedSlides(sessionId: string | null) {
    return useQuery({
        queryKey: queryKeys.generation.slides(sessionId || ""),
        queryFn: async () => {
            const response = await fetch(`/api/generate/slides/${sessionId}`);
            if (!response.ok) {
                throw new Error("Failed to fetch slides");
            }
            return response.json();
        },
        enabled: !!sessionId,
        staleTime: 5 * 60 * 1000, // 5 minutes - slides don't change after generation
    });
}

/**
 * Hook to trigger generation after outline approval
 */
export function useTriggerGeneration(sessionId: string | null) {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async () => {
            const response = await fetch(`/api/generate/generate/${sessionId}`, {
                method: "POST",
            });

            if (!response.ok) {
                throw new Error("Failed to trigger generation");
            }

            return response.json();
        },
        onSuccess: () => {
            if (sessionId) {
                queryClient.invalidateQueries({
                    queryKey: queryKeys.generation.status(sessionId),
                });
            }
        },
    });
}
