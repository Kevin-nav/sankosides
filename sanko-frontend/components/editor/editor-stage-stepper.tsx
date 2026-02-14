"use client";

import { cn } from "@/lib/utils";

type WorkspaceStage = "clarifying" | "blueprint" | "generating" | "completed" | "generation_failed" | string;

const STEPS = ["Brief", "Outline", "Generate", "Review"] as const;

function stageToStepIndex(stage: WorkspaceStage): number {
    const s = (stage || "").toLowerCase();
    if (s === "completed") return 3;
    if (s === "blueprint") return 1;
    if (s === "generating") return 2;
    if (s === "generation_failed" || s === "failed") return 2;
    // Treat everything else (clarifying, scope, processing, etc) as Brief.
    return 0;
}

export function EditorStageStepper({ stage, className }: { stage: WorkspaceStage; className?: string }) {
    const activeIndex = stageToStepIndex(stage);
    return (
        <div className={cn("flex items-center gap-2", className)} aria-label="Editor stages">
            {STEPS.map((label, idx) => (
                <div key={label} className="flex items-center gap-2">
                    <div
                        className={cn(
                            "rounded-full px-2 py-1 text-[10px] font-medium border",
                            idx === activeIndex
                                ? "bg-emerald-500/10 text-emerald-300 border-emerald-500/20"
                                : idx < activeIndex
                                    ? "bg-neutral-900/40 text-neutral-300 border-neutral-800"
                                    : "bg-transparent text-neutral-500 border-neutral-900"
                        )}
                    >
                        {label}
                    </div>
                    {idx < STEPS.length - 1 && (
                        <div className={cn("h-px w-6", idx < activeIndex ? "bg-emerald-500/20" : "bg-neutral-800")} />
                    )}
                </div>
            ))}
        </div>
    );
}

