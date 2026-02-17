/**
 * Convex hooks for Generation Runs (run history / persistence).
 */

import { useMutation, useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";

export interface GenerationRun {
    _id: Id<"generationRuns">;
    projectId: Id<"projects">;
    sessionId: string;
    mode?: string;
    stage: string;
    status?: string;
    brief?: unknown;
    uploads?: unknown;
    scope?: unknown;
    outline?: unknown;
    result?: unknown;
    runtime?: unknown;
    error?: string;
    createdAt: number;
    updatedAt: number;
}

export function useProjectRuns(projectId: Id<"projects"> | null | undefined) {
    return useQuery(
        api.generationRuns.listByProject,
        projectId ? { projectId } : "skip"
    ) as GenerationRun[] | undefined;
}

export function useRun(runId: Id<"generationRuns"> | null | undefined) {
    return useQuery(
        api.generationRuns.get,
        runId ? { id: runId } : "skip"
    ) as GenerationRun | null | undefined;
}

export function useRunBySession(sessionId: string | null | undefined) {
    return useQuery(
        api.generationRuns.getBySession,
        sessionId ? { sessionId } : "skip"
    ) as GenerationRun | null | undefined;
}

export function useCreateRun() {
    return useMutation(api.generationRuns.create);
}

export function useUpdateRun() {
    return useMutation(api.generationRuns.update);
}
