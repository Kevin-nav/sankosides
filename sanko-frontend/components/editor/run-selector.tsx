"use client";

import { useMemo, useState } from "react";
import { formatDistanceToNow } from "date-fns";
import { ChevronDown, History, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Id, useProjectRuns, useUpdateProject, type GenerationRun } from "@/hooks/convex";

function formatRunLabel(run: GenerationRun, indexFromNewest: number) {
    const stage = (run.stage || "").toLowerCase();
    const stageLabel =
        stage === "completed" ? "Review" :
            stage === "generating" ? "Generating" :
                stage === "blueprint" ? "Outline" :
                    stage === "failed" ? "Failed" :
                        "Brief";
    return `Run ${indexFromNewest} · ${stageLabel}`;
}

export function RunSelector({
    projectId,
    activeRunId,
    className,
}: {
    projectId: Id<"projects">;
    activeRunId?: Id<"generationRuns">;
    className?: string;
}) {
    const runs = useProjectRuns(projectId);
    const updateProject = useUpdateProject();
    const [busyRunId, setBusyRunId] = useState<string | null>(null);

    const ordered = useMemo(() => runs ?? [], [runs]);
    const activeRun = useMemo(() => ordered.find((r) => r._id === activeRunId), [ordered, activeRunId]);

    const activeLabel = activeRun ? formatRunLabel(activeRun, ordered.indexOf(activeRun) + 1) : "Runs";

    const onSelect = async (run: GenerationRun) => {
        if (busyRunId) return;
        setBusyRunId(run._id);
        try {
            await updateProject({
                id: projectId,
                activeRunId: run._id,
                sessionId: run.sessionId, // keep legacy field in sync
            });
        } finally {
            setBusyRunId(null);
        }
    };

    return (
        <DropdownMenu>
            <DropdownMenuTrigger asChild>
                <Button
                    variant="outline"
                    size="sm"
                    className={className ?? "border-neutral-800 bg-neutral-950/40 text-neutral-200 hover:bg-neutral-900"}
                >
                    <History className="mr-2 h-4 w-4 text-neutral-400" />
                    <span className="max-w-[180px] truncate">{activeLabel}</span>
                    <ChevronDown className="ml-2 h-4 w-4 text-neutral-500" />
                </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-[320px] bg-neutral-950 border-neutral-800 text-neutral-100">
                <DropdownMenuLabel className="text-neutral-300">Run history</DropdownMenuLabel>
                <DropdownMenuSeparator className="bg-neutral-800" />
                {ordered.length === 0 && (
                    <div className="px-3 py-2 text-xs text-neutral-500">No runs yet.</div>
                )}
                {ordered.map((run, idx) => {
                    const isActive = run._id === activeRunId;
                    const runIndexFromNewest = idx + 1;
                    const subtitle = formatDistanceToNow(new Date(run.createdAt), { addSuffix: true });
                    const label = formatRunLabel(run, runIndexFromNewest);
                    const stage = (run.stage || "").toLowerCase();
                    const stageChip =
                        stage === "completed" ? "Ready" :
                            stage === "generating" ? "Generating" :
                                stage === "blueprint" ? "Outline" :
                                    stage === "failed" ? "Failed" :
                                        "Brief";
                    const disabled = !!busyRunId;
                    return (
                        <DropdownMenuItem
                            key={run._id}
                            disabled={disabled}
                            onSelect={() => void onSelect(run)}
                            className="focus:bg-neutral-900"
                        >
                            <div className="flex w-full items-center gap-2">
                                <div className="flex h-5 w-5 items-center justify-center">
                                    {isActive ? <Check className="h-4 w-4 text-emerald-400" /> : null}
                                </div>
                                <div className="min-w-0 flex-1">
                                    <div className="flex items-center justify-between gap-2">
                                        <div className="truncate text-sm text-neutral-200">{label}</div>
                                        <div className="shrink-0 rounded-full border border-neutral-800 bg-neutral-900/40 px-2 py-0.5 text-[10px] text-neutral-300">
                                            {stageChip}
                                        </div>
                                    </div>
                                    <div className="truncate text-[11px] text-neutral-500">{subtitle}</div>
                                </div>
                            </div>
                        </DropdownMenuItem>
                    );
                })}
            </DropdownMenuContent>
        </DropdownMenu>
    );
}

