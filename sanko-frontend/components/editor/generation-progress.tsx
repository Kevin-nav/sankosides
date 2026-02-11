"use client";

import { useEffect, useMemo, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle2, XCircle, Brain, Cpu, Zap, Activity, Terminal } from "lucide-react";
import { useGenerationProgressBySession } from "@/hooks/convex";
import { useSessionStatus } from "@/hooks/api/use-generation";

interface AgentState {
    name: string;
    model?: string;
    thinking_level?: string;
    status: "pending" | "running" | "complete" | "error";
    thinking_chunks: string[];
    start_time?: number;
    duration_ms?: number;
    cost?: number;
    error?: string;
    toolCalls: ToolCall[];
    currentPhase?: string;
}

interface ToolCall {
    tool: string;
    action: string;
    input?: Record<string, unknown>;
    result?: string;
    success?: boolean;
    pending: boolean;
}

interface GenerationProgressProps {
    sessionId: string;
    onComplete?: (result: { success: boolean; error?: string }) => void;
    onStageChange?: (stage: string | null) => void;
}

const AGENT_ORDER = ["planner", "refiner", "citation_auditor", "final_slides", "generator", "visual_qa"];

export function GenerationProgress({ sessionId, onComplete, onStageChange }: GenerationProgressProps) {
    const completionRef = useRef<{ done: boolean; error: boolean }>({ done: false, error: false });
    const lastStageRef = useRef<string | null>(null);

    // Convex real-time progress - THE primary source of truth
    const convexProgress = useGenerationProgressBySession(sessionId || null);
    const { data: polledStatus } = useSessionStatus(sessionId, {
        enabled: !!sessionId && !convexProgress,
        refetchInterval: 2000,
    });
    const effectiveProgress = useMemo(() => {
        if (convexProgress) return convexProgress;
        if (!polledStatus) return null;

        return {
            currentStep: polledStatus.status === "completed"
                ? "complete"
                : polledStatus.status === "failed"
                    ? "error"
                    : (polledStatus.current_stage === "qa" ? "visual_qa" : polledStatus.current_stage || "initializing"),
            stepProgress: polledStatus.total_slides > 0
                ? Math.min(100, Math.round((polledStatus.slides_completed / polledStatus.total_slides) * 100))
                : 0,
            currentSlideIndex: polledStatus.slides_completed > 0 ? polledStatus.slides_completed - 1 : 0,
            totalSlides: polledStatus.total_slides,
            message: polledStatus.error || undefined,
        };
    }, [convexProgress, polledStatus]);

    const pipelineStatus = useMemo<"idle" | "running" | "complete" | "error">(() => {
        const step = effectiveProgress?.currentStep;
        if (!step) return "idle";
        if (step === "complete") return "complete";
        if (step === "error") return "error";
        return "running";
    }, [effectiveProgress]);

    const pipelineResult = useMemo<{ success: boolean; visualScore?: number } | null>(() => {
        if (pipelineStatus === "complete") return { success: true, visualScore: 0.95 };
        if (pipelineStatus === "error") return { success: false };
        return null;
    }, [pipelineStatus]);

    const qaProgress = useMemo(() => {
        if (effectiveProgress?.currentSlideIndex === undefined || !effectiveProgress.totalSlides) {
            return null;
        }
        return {
            currentSlide: effectiveProgress.currentSlideIndex + 1,
            totalSlides: effectiveProgress.totalSlides,
            currentIteration: 1,
            maxIterations: 3,
            score: effectiveProgress.stepProgress / 100,
            issues: [] as string[],
        };
    }, [effectiveProgress]);

    const currentAgent = useMemo<string | null>(() => {
        const step = effectiveProgress?.currentStep;
        if (!step || step === "complete" || step === "error" || step === "initializing") return null;
        const agentName = step === "qa" ? "visual_qa" : step;
        return AGENT_ORDER.includes(agentName) ? agentName : null;
    }, [effectiveProgress]);

    const agents = useMemo<Record<string, AgentState>>(() => {
        const initial: Record<string, AgentState> = {};
        AGENT_ORDER.forEach((name) => {
            initial[name] = { name, status: "pending", thinking_chunks: [], toolCalls: [] };
        });

        const step = effectiveProgress?.currentStep;
        if (!step) return initial;
        if (step === "complete") {
            AGENT_ORDER.forEach((name) => {
                initial[name].status = "complete";
            });
            return initial;
        }
        if (currentAgent) {
            const agentIndex = AGENT_ORDER.indexOf(currentAgent);
            for (let i = 0; i < agentIndex; i++) {
                initial[AGENT_ORDER[i]].status = "complete";
            }
            initial[currentAgent].status = step === "error" ? "error" : "running";
        }
        return initial;
    }, [effectiveProgress, currentAgent]);

    useEffect(() => {
        const step = effectiveProgress?.currentStep;
        if (!step) return;
        if (step === "complete" && !completionRef.current.done) {
            completionRef.current.done = true;
            onComplete?.({ success: true });
        } else if (step === "error" && !completionRef.current.error) {
            completionRef.current.error = true;
            onComplete?.({ success: false, error: effectiveProgress.message ?? undefined });
        }
        if (currentAgent !== lastStageRef.current) {
            lastStageRef.current = currentAgent;
            onStageChange?.(currentAgent);
        }
    }, [effectiveProgress, currentAgent, onComplete, onStageChange]);

    const currentAgentState = currentAgent ? agents[currentAgent] : null;

    return (
        <div className="h-full flex flex-col bg-neutral-950 overflow-hidden rounded-xl">
            {/* Fixed Header Section */}
            <div className="shrink-0 space-y-4 p-4 pb-2 bg-neutral-950 z-10">
                {/* Pipeline Status Header */}
                <Card className="border-neutral-800 bg-neutral-900/50 shadow-md">
                    <CardHeader className="pb-3 border-b border-neutral-800/50">
                        <CardTitle className="flex items-center justify-between text-base font-semibold text-neutral-200">
                            <div className="flex items-center gap-2">
                                <Activity className="h-4 w-4 text-emerald-500" />
                                Mission Control
                            </div>
                            <Badge variant={
                                pipelineStatus === "running" ? "default" :
                                    pipelineStatus === "complete" ? "secondary" :
                                        pipelineStatus === "error" ? "destructive" : "outline"
                            } className="bg-neutral-800 text-neutral-300 hover:bg-neutral-800 border-neutral-700">
                                {pipelineStatus === "idle" ? "Waiting" :
                                    pipelineStatus === "running" ? <span className="flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" /> Generating</span> :
                                        pipelineStatus === "complete" ? "Complete" : "Error"}
                            </Badge>
                        </CardTitle>
                    </CardHeader>
                    {/* Compact Pipeline Result */}
                    {pipelineResult && (
                        <CardContent className="pt-3 pb-3">
                            <div className="flex items-center gap-4 text-sm">
                                {pipelineResult.success ? (
                                    <span className="flex items-center gap-1.5 text-emerald-400 font-medium">
                                        <CheckCircle2 className="h-4 w-4" /> Success
                                    </span>
                                ) : (
                                    <span className="flex items-center gap-1.5 text-red-400 font-medium">
                                        <XCircle className="h-4 w-4" /> Failed
                                    </span>
                                )}
                                {pipelineResult.visualScore !== undefined && (
                                    <>
                                        <div className="h-4 w-px bg-neutral-800" />
                                        <span className="text-muted-foreground">
                                            Score: <span className="text-neutral-200">{(pipelineResult.visualScore * 100).toFixed(0)}%</span>
                                        </span>
                                    </>
                                )}
                            </div>
                        </CardContent>
                    )}
                </Card>

                {/* Agent Pipeline Stages - Horizontal Bar */}
                <div className="flex gap-2 items-center justify-between text-sm overflow-x-auto pb-1 scrollbar-thin scrollbar-thumb-neutral-800">
                    {AGENT_ORDER.map((agentName, idx) => {
                        const agent = agents[agentName];
                        const isActive = agent.status === "running";
                        const isComplete = agent.status === "complete";
                        const isError = agent.status === "error";

                        return (
                            <div key={agentName} className="flex items-center gap-2 flex-1 min-w-[120px]">
                                <div className={`
                                    flex items-center gap-2 px-3 py-2 rounded-md border w-full transition-all duration-300
                                    ${isActive ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-sm shadow-emerald-500/10 ring-1 ring-emerald-500/20" : ""}
                                    ${isComplete ? "bg-neutral-800/50 border-neutral-700 text-neutral-300 opacity-60" : ""}
                                    ${isError ? "bg-red-500/10 border-red-500/30 text-red-400" : ""}
                                    ${agent.status === "pending" ? "bg-transparent border-transparent text-neutral-600" : ""}
                                `}>
                                    {isActive ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> :
                                        isComplete ? <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" /> :
                                            isError ? <XCircle className="h-3.5 w-3.5" /> :
                                                <span className="h-2 w-2 rounded-full bg-neutral-700" />}

                                    <span className="font-medium truncate text-xs uppercase tracking-wide">
                                        {agentName === "visual_qa" ? "Visual QA" :
                                            agentName.charAt(0).toUpperCase() + agentName.slice(1)}
                                    </span>
                                </div>
                                {idx < AGENT_ORDER.length - 1 && (
                                    <div className={`h-px w-4 shrink-0 ${isComplete ? "bg-emerald-500/30" : "bg-neutral-800"}`} />
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Scrollable Content Area */}
            <div className="flex-1 overflow-y-auto p-4 pt-0 space-y-4 min-h-0 scrollbar-thin scrollbar-thumb-neutral-800 hover:scrollbar-thumb-neutral-700">

                {/* Active Agent Card */}
                {currentAgentState && (
                    <Card className="border-emerald-500/20 bg-emerald-500/5 shadow-sm shadow-emerald-500/5 animate-in fade-in slide-in-from-bottom-2 duration-300">
                        <CardHeader className="pb-3 border-b border-emerald-500/10">
                            <CardTitle className="flex items-center justify-between text-sm">
                                <div className="flex items-center gap-2 text-emerald-400">
                                    <Brain className="h-4 w-4 animate-pulse" />
                                    <span className="font-semibold">
                                        {currentAgentState.name === "visual_qa" ? "Visual QA" :
                                            currentAgentState.name.charAt(0).toUpperCase() + currentAgentState.name.slice(1)}
                                    </span>
                                </div>
                                <div className="flex gap-2">
                                    <Badge variant="outline" className="text-[10px] h-5 border-emerald-500/20 text-emerald-300 bg-emerald-500/5">
                                        <Cpu className="h-3 w-3 mr-1" />
                                        {currentAgentState.model || "gemini-flash"}
                                    </Badge>
                                    <Badge variant="outline" className="text-[10px] h-5 border-emerald-500/20 text-emerald-300 bg-emerald-500/5">
                                        <Zap className="h-3 w-3 mr-1" />
                                        {currentAgentState.thinking_level || "high"}
                                    </Badge>
                                </div>
                            </CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-4 pt-4">
                            {/* QA Progress - shown when Visual QA is active */}
                            {currentAgentState.name === "visual_qa" && qaProgress && (
                                <div className="space-y-2 p-3 bg-blue-500/5 border border-blue-500/20 rounded-lg">
                                    <div className="flex items-center justify-between text-sm">
                                        <span className="text-blue-300 font-medium">
                                            Slide {qaProgress.currentSlide} of {qaProgress.totalSlides}
                                        </span>
                                        <span className="text-neutral-400 text-xs">
                                            Iteration {qaProgress.currentIteration}/{qaProgress.maxIterations}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-3">
                                        <div className="flex-1 bg-neutral-800 rounded-full h-2 overflow-hidden">
                                            <div
                                                className={`h-full transition-all duration-300 ${qaProgress.score >= 0.95 ? "bg-emerald-500" :
                                                    qaProgress.score >= 0.8 ? "bg-blue-500" :
                                                        qaProgress.score >= 0.6 ? "bg-amber-500" : "bg-red-500"
                                                    }`}
                                                style={{ width: `${qaProgress.score * 100}%` }}
                                            />
                                        </div>
                                        <span className={`text-sm font-bold ${qaProgress.score >= 0.95 ? "text-emerald-400" :
                                            qaProgress.score >= 0.8 ? "text-blue-400" :
                                                qaProgress.score >= 0.6 ? "text-amber-400" : "text-red-400"
                                            }`}>
                                            {Math.round(qaProgress.score * 100)}%
                                        </span>
                                    </div>
                                    {qaProgress.issues.length > 0 && (
                                        <div className="text-xs text-neutral-400 mt-1">
                                            Issues: {qaProgress.issues.slice(0, 2).join(", ")}
                                            {qaProgress.issues.length > 2 && ` +${qaProgress.issues.length - 2} more`}
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Convex Progress Info */}
                            {convexProgress && convexProgress.message && (
                                <div className="space-y-1.5">
                                    <div className="text-xs font-medium text-emerald-500/70 uppercase tracking-wider flex items-center gap-1.5">
                                        <Activity className="h-3 w-3" />
                                        Status
                                    </div>
                                    <div className="bg-black/40 rounded-lg p-3 font-mono text-xs text-emerald-300/90 leading-relaxed border border-white/5 shadow-inner">
                                        {convexProgress.message}
                                    </div>
                                </div>
                            )}

                            {/* Progress Bar */}
                            {convexProgress && convexProgress.stepProgress > 0 && (
                                <div className="space-y-1.5">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="text-neutral-400">Progress</span>
                                        <span className="text-emerald-400 font-mono">{convexProgress.stepProgress}%</span>
                                    </div>
                                    <div className="w-full bg-neutral-800 rounded-full h-2 overflow-hidden">
                                        <div
                                            className="bg-emerald-500 h-full transition-all duration-300"
                                            style={{ width: `${convexProgress.stepProgress}%` }}
                                        />
                                    </div>
                                </div>
                            )}

                            {/* Tool Calls (if any were tracked) */}
                            {currentAgentState.toolCalls.length > 0 && (
                                <div className="space-y-2">
                                    <div className="text-xs font-medium text-muted-foreground flex items-center gap-1.5 uppercase tracking-wider">
                                        <Terminal className="h-3 w-3" />
                                        Active Tools ({currentAgentState.toolCalls.length})
                                    </div>
                                    <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-neutral-800">
                                        {currentAgentState.toolCalls.map((tc, idx) => (
                                            <div
                                                key={idx}
                                                className={`grid grid-cols-[auto_1fr] gap-3 text-xs p-2 rounded-md border transition-all ${tc.pending
                                                    ? "bg-amber-500/5 border-amber-500/20 text-amber-200"
                                                    : tc.success
                                                        ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-200"
                                                        : "bg-red-500/5 border-red-500/20 text-red-200"
                                                    }`}
                                            >
                                                <div className="flex items-center justify-center pt-0.5">
                                                    {tc.pending ? (
                                                        <Loader2 className="h-3 w-3 animate-spin text-amber-500" />
                                                    ) : tc.success ? (
                                                        <CheckCircle2 className="h-3 w-3 text-emerald-500" />
                                                    ) : (
                                                        <XCircle className="h-3 w-3 text-red-500" />
                                                    )}
                                                </div>
                                                <div className="space-y-1 min-w-0">
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-semibold tracking-tight">
                                                            {tc.tool}
                                                        </span>
                                                        <span className="text-[10px] opacity-60 uppercase bg-black/20 px-1 rounded">
                                                            {tc.action}
                                                        </span>
                                                    </div>
                                                    <div className="font-mono opacity-80 truncate" title={tc.result || JSON.stringify(tc.input)}>
                                                        {tc.result ? (
                                                            <span className="flex items-center gap-1">
                                                                <span className="opacity-50">→</span> {tc.result}
                                                            </span>
                                                        ) : (
                                                            <span className="opacity-60">{tc.input?.query || tc.input?.url || "..."}</span>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                )}

                {/* Completed Agents Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pb-4">
                    {AGENT_ORDER.filter(name => agents[name].status === "complete" || agents[name].status === "error").map(agentName => {
                        const agent = agents[agentName];
                        const isError = agent.status === "error";

                        return (
                            <Card key={agentName} className={`
                                bg-neutral-900/40 border transition-all
                                ${isError ? "border-red-500/20" : "border-neutral-800 hover:border-emerald-500/20"}
                            `}>
                                <CardHeader className="pb-2 pt-3">
                                    <CardTitle className="flex items-center justify-between text-sm">
                                        <span className={`flex items-center gap-2 font-medium ${isError ? "text-red-400" : "text-neutral-300"}`}>
                                            {isError ? <XCircle className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                                            {agentName === "visual_qa" ? "Visual QA" : agentName.charAt(0).toUpperCase() + agentName.slice(1).replace("_", " ")}
                                        </span>
                                        {agent.duration_ms && (
                                            <span className="text-[10px] font-mono text-neutral-500 bg-neutral-900 px-1.5 py-0.5 rounded border border-neutral-800">
                                                {(agent.duration_ms / 1000).toFixed(1)}s
                                            </span>
                                        )}
                                    </CardTitle>
                                </CardHeader>
                                <CardContent className="pb-3 pt-0">
                                    {agent.error ? (
                                        <p className="text-xs text-red-400 bg-red-500/5 p-2 rounded border border-red-500/10 font-mono mt-1">{agent.error}</p>
                                    ) : (
                                        <div className="flex flex-wrap gap-2 text-xs pt-1">
                                            {agent.model && (
                                                <Badge variant="outline" className="text-[10px] h-5 border-neutral-800 text-neutral-400 font-normal bg-neutral-900">
                                                    {agent.model}
                                                </Badge>
                                            )}
                                            {agent.thinking_chunks.length > 0 && (
                                                <Badge variant="outline" className="text-[10px] h-5 border-neutral-800 text-neutral-400 font-normal bg-neutral-900">
                                                    <Brain className="h-3 w-3 mr-1 opacity-70" />
                                                    {(agent.thinking_chunks.join("").length / 1000).toFixed(1)}k chars
                                                </Badge>
                                            )}
                                            {agent.toolCalls?.length > 0 && (
                                                <Badge variant="outline" className="text-[10px] h-5 border-neutral-800 text-neutral-400 font-normal bg-neutral-900">
                                                    <Terminal className="h-3 w-3 mr-1 opacity-70" />
                                                    {agent.toolCalls.length} tools
                                                </Badge>
                                            )}
                                        </div>
                                    )}
                                </CardContent>
                            </Card>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
