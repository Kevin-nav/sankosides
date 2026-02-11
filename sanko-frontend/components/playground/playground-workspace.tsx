"use client";

import { useState, useEffect } from "react";
import { ClarifierChat } from "@/components/editor/clarifier-chat";
import { BlueprintReview } from "@/components/editor/blueprint-review";
import { GenerationProgress } from "@/components/editor/generation-progress";
import { SlideViewer } from "@/components/editor/slide-viewer";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Loader2, RefreshCcw, Save, Play, Terminal, Check, Settings2, Activity } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Group, Panel } from "react-resizable-panels";
import { ResizeHandle } from "./resize-handle";
import React from "react";
import { MetricsDashboard } from "./metrics-dashboard";
import { cn } from "@/lib/utils";
import { Brain, Sparkles, BookOpen, FileText, Layers, Eye, ChevronRight } from "lucide-react";
import { useCreateProject } from "@/hooks/convex";
import { Id } from "@/convex/_generated/dataModel";

const PipelineStages = ({ currentStage }: { currentStage: string | null }) => {
    const stages = [
        { id: 'planner', label: 'Planner', icon: Brain },
        { id: 'refiner', label: 'Refiner', icon: Sparkles },
        { id: 'citation_auditor', label: 'Citations', icon: BookOpen },
        { id: 'final_slides', label: 'Final', icon: FileText },
        { id: 'generator', label: 'Generator', icon: Layers },
        { id: 'visual_qa', label: 'QA', icon: Eye },
    ];

    return (
        <div className="flex items-center gap-1 px-4 py-2 bg-neutral-900/50 border-b border-white/5 overflow-x-auto custom-scrollbar">
            {stages.map((stage, idx) => (
                <React.Fragment key={stage.id}>
                    <div className={cn(
                        "flex items-center gap-1.5 px-2 py-1 rounded text-[10px] font-mono uppercase whitespace-nowrap transition-colors",
                        currentStage === stage.id
                            ? "bg-emerald-500/20 text-emerald-400 animate-pulse border border-emerald-500/20"
                            : "text-neutral-600"
                    )}>
                        <stage.icon className="w-3 h-3" />
                        <span>{stage.label}</span>
                    </div>
                    {idx < stages.length - 1 && (
                        <ChevronRight className="w-3 h-3 text-neutral-800 flex-shrink-0" />
                    )}
                </React.Fragment>
            ))}
        </div>
    );
};

interface PromptRegistry {
    CLARIFIER_SYSTEM: string;
    BLUEPRINT_GENERATION: string;
    [key: string]: string;
}

interface MetricsSummary {
    total_agents: number;
    successful_agents: number;
    failed_agents: number;
    total_tokens: number;
    total_input_tokens: number;
    total_output_tokens: number;
    total_thinking_tokens: number;
    total_duration_ms: number;
    total_cost_usd: number;
    agents: Record<string, {
        status?: string;
        model?: string;
        total_tokens?: number;
    }>;
}

export function PlaygroundWorkspace() {
    const { convexUserId } = useAuth();
    const createProject = useCreateProject();

    // Configuration State
    const [prompts, setPrompts] = useState<PromptRegistry | null>(null);
    const [selectedPromptKey, setSelectedPromptKey] = useState<string>("CLARIFIER_SYSTEM");
    const [editedPrompts, setEditedPrompts] = useState<Record<string, string>>({});
    const [topic, setTopic] = useState<string>("The Future of AI Agents");
    const [isLoadingPrompts, setIsLoadingPrompts] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [saveSuccess, setSaveSuccess] = useState(false);

    // Simulation State
    const [sessionKey, setSessionKey] = useState(0);
    const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
    const [showBlueprint, setShowBlueprint] = useState(false);
    const [isGenerating, setIsGenerating] = useState(false);
    const [isCompleted, setIsCompleted] = useState(false);
    const [viewMode, setViewMode] = useState<'chat' | 'blueprint' | 'generating' | 'result'>('chat');

    // Telemetry State
    const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
    const [activeAgent, setActiveAgent] = useState<string | null>(null);
    const [currentThinking, setCurrentThinking] = useState<string>("");
    const [currentStage, setCurrentStage] = useState<string | null>(null);

    // Convex Project State - for real-time progress tracking
    const [convexProjectId, setConvexProjectId] = useState<Id<"projects"> | null>(null);
    const [isCreatingProject, setIsCreatingProject] = useState(false);

    // Initialize View Mode logic
    useEffect(() => {
        if (isCompleted && activeSessionId) setViewMode('result');
        else if (isGenerating) setViewMode('generating');
        else if (showBlueprint) setViewMode('blueprint');
        else setViewMode('chat');
    }, [isCompleted, isGenerating, showBlueprint, activeSessionId]);

    // Auto-create Convex project on initial load for real-time tracking
    useEffect(() => {
        if (!convexUserId || convexProjectId || isCreatingProject) return;

        async function createInitialProject() {
            setIsCreatingProject(true);
            try {
                const newProjectId = await createProject({
                    title: `Playground: ${topic || 'Untitled'}`,
                    description: "Auto-created by playground for real-time tracking",
                    userId: convexUserId!,
                });
                setConvexProjectId(newProjectId);
                console.log("[Playground] Created Convex project for real-time tracking:", newProjectId);
            } catch (e) {
                console.warn("[Playground] Failed to create Convex project:", e);
            } finally {
                setIsCreatingProject(false);
            }
        }

        createInitialProject();
    }, [convexUserId, convexProjectId, isCreatingProject, topic, createProject]);

    // Data Fetching
    useEffect(() => {
        async function fetchPrompts() {
            try {
                const res = await fetch("/api/generate/prompts");
                if (res.ok) {
                    const data = await res.json();
                    setPrompts(data);

                    // Load custom overrides
                    try {
                        const customRes = await fetch("/api/generate/prompts/custom");
                        if (customRes.ok) {
                            const customData = await customRes.json();
                            setEditedPrompts(Object.keys(customData).length > 0
                                ? { ...data, ...customData }
                                : data);
                        } else {
                            setEditedPrompts(data);
                        }
                    } catch {
                        setEditedPrompts(data);
                    }
                } else {
                    throw new Error("API Failed");
                }
            } catch (e) {
                console.error("Failed to fetch prompts, using mocks", e);
                setPrompts({
                    "CLARIFIER_SYSTEM": "You are an expert presentation architect...",
                    "BLUEPRINT_GENERATION": "Create a detailed slide breakdown..."
                });
                setEditedPrompts({
                    "CLARIFIER_SYSTEM": "You are an expert presentation architect...",
                    "BLUEPRINT_GENERATION": "Create a detailed slide breakdown..."
                });
            } finally {
                setIsLoadingPrompts(false);
            }
        }
        fetchPrompts();
    }, []);

    // Static metrics placeholder - remove polling to reduce server load
    // TODO: Migrate to Convex subscription if real-time metrics are needed
    useEffect(() => {
        setMetrics({
            total_agents: 0,
            successful_agents: 0,
            failed_agents: 0,
            total_tokens: 0,
            total_input_tokens: 0,
            total_output_tokens: 0,
            total_thinking_tokens: 0,
            total_duration_ms: 0,
            total_cost_usd: 0,
            agents: {}
        });
    }, []);

    const handlePromptChange = (val: string) => {
        setEditedPrompts(prev => ({ ...prev, [selectedPromptKey]: val }));
    };

    const handleReset = async () => {
        setSessionKey(prev => prev + 1);
        setActiveSessionId(null);
        setShowBlueprint(false);
        setIsGenerating(false);
        setIsCompleted(false);
        setViewMode('chat');
        setCurrentStage(null);
        setActiveAgent(null);
        setCurrentThinking("");
        setConvexProjectId(null);

        // Create a new Convex project for this session
        if (convexUserId) {
            setIsCreatingProject(true);
            try {
                const newProjectId = await createProject({
                    title: `Playground: ${topic || 'Untitled'}`,
                    description: "Auto-created by playground for testing",
                    userId: convexUserId,
                });
                setConvexProjectId(newProjectId);
                console.log("[Playground] Created Convex project:", newProjectId);
            } catch (e) {
                console.warn("[Playground] Failed to create Convex project, continuing without:", e);
            } finally {
                setIsCreatingProject(false);
            }
        }
    };

    const handleSavePrompts = async () => {
        setIsSaving(true);
        setSaveSuccess(false);
        try {
            const res = await fetch("/api/generate/prompts/save", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompts: editedPrompts })
            });
            if (res.ok) {
                setSaveSuccess(true);
                setTimeout(() => setSaveSuccess(false), 2000);
            }
        } catch (e) {
            console.error("Failed to save prompts", e);
        } finally {
            setIsLoadingPrompts(false); // Should be setIsSaving(false), but keeping logic safe
            setIsSaving(false);
        }
    };

    const handleOrderComplete = (sessionId: string) => {
        setActiveSessionId(sessionId);
        setShowBlueprint(true);
    };

    const handleApprove = async () => {
        setIsGenerating(true);
    };

    const handleGenerationComplete = () => {
        setIsGenerating(false);
        setIsCompleted(true);
    };

    if (isLoadingPrompts) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-black">
                <div className="flex flex-col items-center gap-4">
                    <Loader2 className="w-10 h-10 text-emerald-500 animate-spin" />
                    <span className="text-sm font-mono text-emerald-500/80 animate-pulse">
                        INITIALIZING MISSION CONTROL...
                    </span>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen w-full pt-16 bg-black text-neutral-200 overflow-hidden font-sans selection:bg-emerald-500/30">
            {/* Background Grid/Noise */}
            <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center [mask-image:linear-gradient(180deg,white,rgba(255,255,255,0))]" />
            <div className="absolute inset-0 bg-neutral-950/90" />

            <div className="relative h-full flex flex-col z-10">
                <Group className="h-full" orientation="horizontal">

                    {/* LEFT PANEL: CONFIGURATION */}
                    <Panel defaultSize={20} minSize={10} className="glass-panel flex flex-col order-1">
                        <div className="h-12 border-b border-white/5 flex items-center justify-between px-4 bg-white/5">
                            <div className="flex items-center gap-2 text-emerald-400">
                                <Settings2 className="w-4 h-4" />
                                <span className="text-xs font-bold tracking-wider uppercase">Mission Params</span>
                            </div>
                            <div className="flex gap-1">
                                <Button variant="ghost" size="icon" className="h-6 w-6 hover:bg-white/10" onClick={() => setEditedPrompts(prompts || {})}>
                                    <RefreshCcw className="w-3 h-3 text-neutral-400" />
                                </Button>
                                <Button
                                    variant="ghost"
                                    size="icon"
                                    className={cn("h-6 w-6 hover:bg-white/10", saveSuccess && "text-emerald-400")}
                                    onClick={handleSavePrompts}
                                    disabled={isSaving}
                                >
                                    {isSaving ? <Loader2 className="w-3 h-3 animate-spin" /> : saveSuccess ? <Check className="w-3 h-3" /> : <Save className="w-3 h-3" />}
                                </Button>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">
                            <div className="space-y-2 group">
                                <label className="text-[10px] font-mono text-neutral-500 uppercase tracking-widest group-focus-within:text-emerald-500 transition-colors">Target Objective (Topic)</label>
                                <input
                                    className="w-full bg-transparent border-b border-white/10 py-2 text-sm text-white placeholder:text-neutral-700 focus:outline-none focus:border-emerald-500/50 transition-colors"
                                    value={topic}
                                    onChange={(e) => setTopic(e.target.value)}
                                    placeholder="Enter a topic..."
                                />
                            </div>

                            <div className="space-y-2">
                                <label className="text-[10px] font-mono text-neutral-500 uppercase tracking-widest">Protocol (Prompt)</label>
                                <Select value={selectedPromptKey} onValueChange={setSelectedPromptKey}>
                                    <SelectTrigger className="bg-white/5 border-white/10 text-neutral-200 h-8 text-xs font-mono">
                                        <SelectValue />
                                    </SelectTrigger>
                                    <SelectContent className="bg-neutral-900 border-neutral-800 text-neutral-200">
                                        {prompts && Object.keys(prompts).map(key => (
                                            <SelectItem key={key} value={key} className="font-mono text-xs">{key}</SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>
                            </div>

                            <div className="space-y-2 flex-1 flex flex-col h-[calc(100vh-300px)]">
                                <label className="text-[10px] font-mono text-neutral-500 uppercase tracking-widest flex items-center justify-between">
                                    <span>Override Instructions</span>
                                    <span className="text-[9px] text-amber-500/80 bg-amber-500/10 px-1 rounded">MODIFIED</span>
                                </label>
                                <div className="flex-1 relative group">
                                    <div className="absolute inset-0 bg-emerald-500/5 opacity-0 group-focus-within:opacity-100 transition-opacity pointer-events-none rounded-md" />
                                    <Textarea
                                        className="h-full bg-black/40 border-white/10 font-mono text-xs leading-relaxed text-emerald-100/80 p-3 resize-none focus:ring-1 focus:ring-emerald-500/30 focus:border-emerald-500/30 scrollbar-dark"
                                        value={editedPrompts[selectedPromptKey] || ""}
                                        onChange={(e) => handlePromptChange(e.target.value)}
                                        spellCheck={false}
                                    />
                                </div>
                            </div>
                        </div>
                    </Panel>

                    <ResizeHandle />

                    {/* MIDDLE PANEL: MAIN DISPLAY */}
                    <Panel defaultSize={50} minSize={20} className="flex flex-col relative bg-gradient-to-b from-neutral-950 to-black order-2">
                        {/* HUD Header */}
                        <div className="h-12 border-b border-white/5 bg-white/[0.02] flex items-center justify-between px-4">
                            <div className="flex items-center gap-3">
                                <div className={cn("w-2 h-2 rounded-full shadow-lg transition-all duration-500",
                                    activeSessionId ? "bg-emerald-500 shadow-emerald-500/50" : "bg-neutral-700"
                                )} />
                                <span className="font-mono text-xs text-neutral-400 uppercase tracking-wider">
                                    SESSION ID: <span className="text-white ml-2">{activeSessionId ? activeSessionId.slice(0, 8) : "WAITING"}</span>
                                </span>
                            </div>
                            <Button
                                size="sm"
                                variant="outline"
                                onClick={handleReset}
                                className="h-7 text-xs border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/10 hover:text-emerald-300 transition-colors uppercase tracking-wider font-mono"
                            >
                                <Play className="w-3 h-3 mr-2" /> Initialize New
                            </Button>
                        </div>

                        {/* Viewport */}
                        <div className="flex-1 relative overflow-hidden flex flex-col">
                            {viewMode === 'chat' && (
                                <div className="animate-in fade-in zoom-in-95 duration-500 h-full">
                                    {isCreatingProject || !convexProjectId ? (
                                        <div className="h-full flex items-center justify-center">
                                            <div className="text-center space-y-2">
                                                <Loader2 className="w-6 h-6 animate-spin text-emerald-500 mx-auto" />
                                                <p className="text-sm text-neutral-400 font-mono">
                                                    {isCreatingProject ? "Creating project..." : "Waiting for authentication..."}
                                                </p>
                                            </div>
                                        </div>
                                    ) : (
                                        <ClarifierChat
                                            key={`chat-${sessionKey}`}
                                            projectId={convexProjectId}
                                            mode="deep_research"
                                            topic={topic}
                                            onOrderComplete={handleOrderComplete}
                                            promptOverrides={editedPrompts}
                                            onAgentChange={setActiveAgent}
                                            onThinkingUpdate={setCurrentThinking}
                                        />
                                    )}
                                </div>
                            )}

                            {viewMode === 'blueprint' && (
                                <div className="h-full flex flex-col animate-in slide-in-from-bottom-5 duration-500">
                                    <div className="h-8 bg-emerald-500/10 border-b border-emerald-500/20 flex items-center justify-between px-4">
                                        <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-widest flex items-center gap-2">
                                            <Activity className="w-3 h-3" /> Blueprint Analysis
                                        </span>
                                        <Button variant="ghost" size="sm" onClick={() => setViewMode('chat')} className="h-6 text-[10px] text-neutral-400 hover:text-white">
                                            Back to Comms
                                        </Button>
                                    </div>
                                    <div className="flex-1 overflow-hidden relative">
                                        {activeSessionId && (
                                            <BlueprintReview
                                                sessionId={activeSessionId}
                                                onApprove={handleApprove}
                                            />
                                        )}
                                    </div>
                                </div>
                            )}

                            {viewMode === 'generating' && (
                                <div className="h-full animate-in fade-in duration-700 flex flex-col">
                                    <PipelineStages currentStage={currentStage} />
                                    <div className="flex-1 relative">
                                        {activeSessionId && (
                                            <GenerationProgress
                                                sessionId={activeSessionId}
                                                convexProjectId={convexProjectId || undefined}
                                                onComplete={handleGenerationComplete}
                                                onStageChange={setCurrentStage}
                                            />
                                        )}
                                    </div>
                                </div>
                            )}

                            {viewMode === 'result' && (
                                <div className="h-full animate-in zoom-in-95 duration-500 p-6 bg-neutral-950">
                                    <div className="glass-card h-full overflow-hidden border-emerald-500/20 shadow-[0_0_50px_rgba(16,185,129,0.1)]">
                                        <SlideViewer sessionId={activeSessionId!} />
                                    </div>
                                </div>
                            )}
                        </div>
                    </Panel>



                    <ResizeHandle />

                    {/* RIGHT PANEL: TELEMETRY */}
                    <Panel defaultSize={30} minSize={10} className="glass-panel border-l bg-black/60 flex flex-col order-3">
                        <div className="h-12 border-b border-white/5 flex items-center justify-between px-4 bg-white/[0.02]">
                            <div className="flex items-center gap-2 text-indigo-400">
                                <Terminal className="w-4 h-4" />
                                <span className="text-xs font-bold tracking-wider uppercase">Live Telemetry</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                                <span className="text-[10px] font-mono text-neutral-500">
                                    {activeAgent ? `AGENT: ${activeAgent}` : "CONN_EST"}
                                </span>
                            </div>
                        </div>

                        <div className="flex-1 overflow-y-auto p-4 space-y-6 custom-scrollbar">

                            {/* Live Thinking Log */}
                            <div className="glass-card p-0 overflow-hidden border-indigo-500/20 bg-indigo-950/5">
                                <div className="bg-indigo-500/10 px-3 py-2 border-b border-indigo-500/20 flex items-center justify-between">
                                    <span className="text-[10px] font-mono text-indigo-300 uppercase flex items-center gap-2">
                                        <Brain className="w-3 h-3" /> Cognitive Stream
                                    </span>
                                    {currentThinking && <Activity className="w-3 h-3 text-indigo-400 animate-pulse" />}
                                </div>
                                <div className="p-3 h-48 overflow-y-auto font-mono text-[10px] leading-relaxed text-indigo-200/80 custom-scrollbar">
                                    {currentThinking ? (
                                        <div className="whitespace-pre-wrap animate-pulse-glow">{currentThinking}</div>
                                    ) : (
                                        <span className="text-indigo-500/40 italic">{"// Awaiting neural activation..."}</span>
                                    )}
                                </div>
                            </div>

                            <MetricsDashboard metrics={metrics} />

                        </div>
                    </Panel>

                </Group>
            </div>
        </div>
    );
}
