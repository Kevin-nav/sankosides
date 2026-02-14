"use client";

import { useMemo } from "react";
import { formatDistanceToNow } from "date-fns";
import { Check, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { Id, useProjectRuns, useUpdateProject, type GenerationRun } from "@/hooks/convex";

function stageChip(stageRaw: string | undefined) {
    const stage = (stageRaw || "").toLowerCase();
    if (stage === "completed") return { label: "Ready", cls: "border-emerald-500/20 bg-emerald-500/10 text-emerald-300" };
    if (stage === "generating") return { label: "Generating", cls: "border-blue-500/20 bg-blue-500/10 text-blue-200" };
    if (stage === "blueprint") return { label: "Outline", cls: "border-neutral-700 bg-neutral-900/40 text-neutral-200" };
    if (stage === "failed") return { label: "Failed", cls: "border-red-500/20 bg-red-500/10 text-red-200" };
    return { label: "Brief", cls: "border-neutral-800 bg-neutral-950/30 text-neutral-300" };
}

function labelFor(run: GenerationRun, indexFromNewest: number) {
    const chip = stageChip(run.stage);
    return { title: `Run ${indexFromNewest}`, chip: chip.label, chipCls: chip.cls };
}

export function RunResumePanel({
    projectId,
    activeRunId,
    onRetryGeneration,
    showRetry,
    className,
}: {
    projectId: Id<"projects">;
    activeRunId?: Id<"generationRuns">;
    showRetry?: boolean;
    onRetryGeneration?: () => void;
    className?: string;
}) {
    const runs = useProjectRuns(projectId);
    const updateProject = useUpdateProject();

    const ordered = useMemo(() => runs ?? [], [runs]);

    const setActive = async (run: GenerationRun) => {
        await updateProject({
            id: projectId,
            activeRunId: run._id,
            sessionId: run.sessionId,
        });
    };

    return (
        <div className={cn("flex h-full flex-col bg-neutral-950 p-4", className)}>
            <div className="text-xs uppercase tracking-wider text-neutral-500">Run history</div>

            {showRetry && onRetryGeneration && (
                <Button
                    onClick={onRetryGeneration}
                    className="mt-3 bg-emerald-600 hover:bg-emerald-500 text-white"
                >
                    <RotateCcw className="mr-2 h-4 w-4" />
                    Retry generation
                </Button>
            )}

            <div className="mt-3 space-y-2 overflow-y-auto scrollbar-thin scrollbar-thumb-neutral-800">
                {ordered.length === 0 && (
                    <div className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-3 text-xs text-neutral-500">
                        No runs yet.
                    </div>
                )}

                {ordered.map((run, idx) => {
                    const isActive = run._id === activeRunId;
                    const runIndexFromNewest = idx + 1;
                    const { title, chip, chipCls } = labelFor(run, runIndexFromNewest);
                    const subtitle = formatDistanceToNow(new Date(run.createdAt), { addSuffix: true });
                    return (
                        <button
                            key={run._id}
                            type="button"
                            onClick={() => void setActive(run)}
                            className={cn(
                                "w-full text-left rounded-lg border p-3 transition-colors",
                                isActive
                                    ? "border-emerald-500/30 bg-emerald-500/5"
                                    : "border-neutral-800 bg-neutral-900/20 hover:bg-neutral-900/40"
                            )}
                        >
                            <div className="flex items-center justify-between gap-2">
                                <div className="min-w-0">
                                    <div className="flex items-center gap-2">
                                        {isActive && <Check className="h-4 w-4 text-emerald-400" />}
                                        <div className="truncate text-sm text-neutral-200">{title}</div>
                                    </div>
                                    <div className="truncate text-[11px] text-neutral-500">{subtitle}</div>
                                </div>
                                <div className={cn("shrink-0 rounded-full border px-2 py-0.5 text-[10px]", chipCls)}>
                                    {chip}
                                </div>
                            </div>
                            {run.error && (
                                <div className="mt-2 text-[11px] text-red-200/80 line-clamp-2">{run.error}</div>
                            )}
                        </button>
                    );
                })}
            </div>

            <div className="mt-auto pt-4">
                <Button
                    variant="outline"
                    className="w-full border-neutral-800 text-neutral-200"
                    onClick={async () => {
                        // Switch to the newest run (if any).
                        const newest = ordered[0];
                        if (newest) await setActive(newest);
                    }}
                    disabled={ordered.length === 0}
                >
                    Resume newest run
                </Button>
            </div>
        </div>
    );
}

