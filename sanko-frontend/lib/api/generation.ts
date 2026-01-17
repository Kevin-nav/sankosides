// lib/api/generation.ts
// Generation API functions for SankoSlides

import { api, getAPIUrl } from '../api-client';
import type {
    StartSessionResponse,
    ClarifyResponse,
    OutlineResponse,
    GenerationStartResponse,
    SessionStatusResponse,
    GenerationResult,
    MetricsSummary,
    Modification,
} from '@/types/generation';

/**
 * Generation API module
 * All functions interact with the SankoSlides backend generation endpoints
 */
export const generationApi = {
    /**
     * Start a new generation session
     */
    startSession: (params?: {
        project_id?: string;
        mode?: string;
        topic?: string;
        prompt_overrides?: Record<string, string>;
    }) =>
        api.post<StartSessionResponse>('/api/generation/start', params),

    /**
     * Continue the clarification conversation
     */
    clarify: (sessionId: string, message: string) =>
        api.post<ClarifyResponse>(`/api/generation/clarify/${sessionId}`, {
            message,
        }),

    /**
     * Generate the outline for review
     */
    getOutline: (sessionId: string) =>
        api.post<OutlineResponse>(`/api/generation/outline/${sessionId}`),

    /**
     * Approve outline with optional modifications
     */
    approveOutline: (sessionId: string, modifications?: Modification[]) =>
        api.post<OutlineResponse>(`/api/generation/approve-outline/${sessionId}`, {
            modifications,
        }),

    /**
     * Start the async generation pipeline
     */
    startGeneration: (sessionId: string) =>
        api.post<GenerationStartResponse>(`/api/generation/generate/${sessionId}`),

    /**
     * Get current session status
     */
    getStatus: (sessionId: string) =>
        api.get<SessionStatusResponse>(`/api/generation/status/${sessionId}`),

    /**
     * Get the final generated presentation
     */
    getResult: (sessionId: string) =>
        api.get<GenerationResult>(`/api/generation/result/${sessionId}`),

    /**
     * Get token metrics summary
     */
    getMetrics: (sessionId: string) =>
        api.get<MetricsSummary>(`/api/generation/metrics/${sessionId}/summary`),

    /**
     * Quick start - skip clarification (for demos)
     */
    quickStart: (title: string, topic: string, slidesCount = 8, audience = 'general') =>
        api.post<GenerationStartResponse>(
            `/api/generation/quick-start?title=${encodeURIComponent(title)}&topic=${encodeURIComponent(topic)}&slides_count=${slidesCount}&audience=${encodeURIComponent(audience)}`
        ),

    /**
     * Get the SSE stream URL for a session
     */
    getStreamUrl: (sessionId: string) =>
        `${getAPIUrl()}/api/generation/stream/${sessionId}`,
};
