"use client";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, Loader2, RotateCcw } from "lucide-react";
import { WizardClarifier } from "./wizard-clarifier";
import { BlueprintReview } from "./blueprint-review";
import { GenerationProgress } from "./generation-progress";
import { SlideViewer } from "./slide-viewer";
import { EditorLayout } from "./editor-layout";
import { StageTransitionLoader } from "./stage-transition-loader";
import { useProject, useUpdateProject, useGenerationProgress, useRun, useRunBySession, useCreateRun, useUpdateRun, Id } from "@/hooks/convex";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { EditorStageStepper } from "./editor-stage-stepper";
import { RunSelector } from "./run-selector";
import { RunResumePanel } from "./run-resume-panel";

type EditorStage = "clarifying" | "blueprint" | "generating" | "completed" | "generation_failed";

interface EditorWorkspaceProps {
    projectId: string;
}

const stageVariants = {
    initial: { opacity: 0, y: 20, scale: 0.98 },
    animate: {
        opacity: 1,
        y: 0,
        scale: 1,
        transition: { duration: 0.4, ease: "easeOut" as const },
    },
    exit: {
        opacity: 0,
        y: -20,
        scale: 0.98,
        transition: { duration: 0.3, ease: "easeIn" as const },
    },
};

function mapStatusToStage(status: string | undefined, currentStep?: string): EditorStage {
    const normalized = (status || "").toLowerCase();
    const step = (currentStep || "").toLowerCase();

    if (normalized === "failed" || step === "error") return "generation_failed";
    if (normalized === "completed" || step === "complete") return "completed";
    if (normalized === "generating" || normalized === "qa_in_progress") return "generating";
    if (normalized === "awaiting_outline_approval" || normalized === "outline_approved" || normalized === "clarification_complete") {
        return "blueprint";
    }
    return "clarifying";
}

function getSessionStorageKey(projectId: string) {
    return `editor-session:${projectId}`;
}

export function EditorWorkspace({ projectId }: EditorWorkspaceProps) {
    const project = useProject(projectId as Id<"projects">);
    const updateProject = useUpdateProject();
    const progress = useGenerationProgress(projectId as Id<"projects">);
    const createRun = useCreateRun();
    const updateRun = useUpdateRun();

    const activeRun = useRun(project?.activeRunId as Id<"generationRuns"> | undefined);

    const [stage, setStage] = useState<EditorStage>("clarifying");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isTransitioning, setIsTransitioning] = useState(false);
    const [transitionMessage, setTransitionMessage] = useState("");
    const [generationError, setGenerationError] = useState<string | null>(null);
    const [isResuming, setIsResuming] = useState(true);

    const initializedRef = useRef(false);
    const runBootstrapRef = useRef<{ attempted: boolean; created: boolean }>({ attempted: false, created: false });
    const lastActiveRunRef = useRef<string | null>(null);
    const loading = project === undefined;

    const runBySession = useRunBySession(sessionId || null);
    const effectiveRunId = (project?.activeRunId ?? runBySession?._id) as Id<"generationRuns"> | undefined;

    useEffect(() => {
        if (!project || initializedRef.current) return;
        // If the project points to an active run, wait for it to load so we can use its sessionId deterministically.
        if (project.activeRunId && activeRun === undefined) return;

        initializedRef.current = true;

        const key = getSessionStorageKey(projectId);
        const persistedSessionId = typeof window !== "undefined" ? window.localStorage.getItem(key) : null;
        const candidateSessionId = activeRun?.sessionId || project.sessionId || persistedSessionId;

        if (!candidateSessionId) {
            setStage("clarifying");
            setIsResuming(false);
            return;
        }

        setSessionId(candidateSessionId);

        const bootstrap = async () => {
            try {
                const statusRes = await fetch(`/api/generate/status/${candidateSessionId}`);
                if (!statusRes.ok) {
                    if (statusRes.status === 404 && typeof window !== "undefined") {
                        window.localStorage.removeItem(key);
                    }
                    // Fall back to persisted run stage (best effort) if backend is unavailable.
                    const fallback = (activeRun?.stage || "").toLowerCase();
                    if (fallback === "completed") setStage("completed");
                    else if (fallback === "generating") setStage("generating");
                    else if (fallback === "blueprint") setStage("blueprint");
                    else if (fallback === "failed") setStage("generation_failed");
                    else setStage("clarifying");
                    return;
                }

                const statusData = await statusRes.json();
                const inferredStage = mapStatusToStage(statusData.status, progress?.currentStep || statusData.current_stage);
                setStage(inferredStage);

                const backendError =
                    typeof statusData.error === "string"
                        ? statusData.error
                        : typeof statusData.detail === "string"
                            ? statusData.detail
                            : null;
                setGenerationError(backendError);
            } catch {
                setStage("clarifying");
            } finally {
                setIsResuming(false);
            }
        };

        void bootstrap();
    }, [project, projectId, progress?.currentStep, activeRun, activeRun?.sessionId, activeRun?.stage]);

    // If user switches runs from the header dropdown, reset local state and re-bootstrap.
    useEffect(() => {
        const activeKey = project?.activeRunId ? String(project.activeRunId) : null;
        if (!project) return;
        if (lastActiveRunRef.current === null) {
            lastActiveRunRef.current = activeKey;
            return;
        }
        if (lastActiveRunRef.current === activeKey) return;

        lastActiveRunRef.current = activeKey;
        initializedRef.current = false;
        runBootstrapRef.current = { attempted: false, created: false };
        setIsResuming(true);
        setGenerationError(null);
        setSessionId(null);
        setStage("clarifying");
    }, [project?.activeRunId, project]);

    useEffect(() => {
        if (!sessionId) return;

        const key = getSessionStorageKey(projectId);
        if (typeof window !== "undefined") {
            window.localStorage.setItem(key, sessionId);
        }

        if (project && project.sessionId !== sessionId) {
            void updateProject({ id: project._id, sessionId });
        }
    }, [sessionId, projectId, project, updateProject]);

    // Bootstrap run history for legacy projects (sessionId exists but no generationRuns record).
    useEffect(() => {
        if (!project || !sessionId) return;
        // Wait for the Convex query to resolve: `undefined` means "loading".
        if (runBySession === undefined) return;
        if (runBootstrapRef.current.attempted) return;

        runBootstrapRef.current.attempted = true;

        const ensureRun = async () => {
            try {
                // If project already points at a run, do nothing.
                if (project.activeRunId) return;

                // If run exists by session, bind it.
                if (runBySession?._id) {
                    await updateProject({ id: project._id, activeRunId: runBySession._id });
                    return;
                }

                // Otherwise create a run and bind it.
                const runId = await createRun({
                    projectId: project._id,
                    sessionId,
                    stage: stage === "generation_failed" ? "failed" : stage,
                });
                runBootstrapRef.current.created = true;
                await updateProject({ id: project._id, activeRunId: runId as Id<"generationRuns"> });
            } catch (e) {
                console.error("Failed to bootstrap generation run:", e);
            }
        };

        void ensureRun();
    }, [project, sessionId, runBySession, createRun, updateProject, stage]);

    // Persist stage changes to the active run (best effort).
    useEffect(() => {
        if (!effectiveRunId) return;
        if (isTransitioning) return;

        const persist = async () => {
            try {
                await updateRun({
                    id: effectiveRunId,
                    stage: stage === "generation_failed" ? "failed" : stage,
                    status: stage === "completed" ? "completed" : stage === "generation_failed" ? "failed" : "active",
                    error: stage === "generation_failed" ? (generationError ?? undefined) : undefined,
                });
            } catch (e) {
                console.error("Failed to persist run stage:", e);
            }
        };

        void persist();
    }, [effectiveRunId, stage, isTransitioning, updateRun, generationError]);

    if (loading || isResuming) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-black">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center gap-4"
                >
                    <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
                    <span className="text-neutral-400 text-sm">Loading project...</span>
                </motion.div>
            </div>
        );
    }

    if (project === null) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-black">
                <div className="flex flex-col items-center gap-4">
                    <span className="text-neutral-300">Project not found or deleted.</span>
                    <Link href="/dashboard">
                        <Button className="bg-emerald-600 hover:bg-emerald-500 text-white">
                            Back to dashboard
                        </Button>
                    </Link>
                </div>
            </div>
        );
    }

    const transitionToStage = (newStage: EditorStage, message?: string) => {
        setIsTransitioning(true);
        setTransitionMessage(message || "");

        setTimeout(() => {
            setStage(newStage);
            setIsTransitioning(false);
        }, 700);
    };

    const onClarificationComplete = (sid: string) => {
        setSessionId(sid);
        setGenerationError(null);
        transitionToStage("blueprint", "Creating your presentation blueprint...");
    };

    const onBlueprintApproved = () => {
        setGenerationError(null);
        transitionToStage("generating", "Starting AI generation...");
    };

    const onGenerationComplete = (result: { success: boolean; error?: string }) => {
        if (result.success) {
            setGenerationError(null);
            transitionToStage("completed", "Finalizing your presentation...");
            return;
        }

        setGenerationError(result.error || "Generation failed. You can retry or return to blueprint.");
        transitionToStage("generation_failed");
    };

    const onRetryGeneration = async () => {
        if (!sessionId) return;

        setGenerationError(null);
        try {
            const response = await fetch(`/api/generate/generate/${sessionId}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });

            if (response.ok) {
                transitionToStage("generating", "Restarting generation...");
                return;
            }

            const payload = await response.json().catch(() => ({}));
            const detail = typeof payload.detail === "string" ? payload.detail : "Generation retry failed.";
            setGenerationError(detail);
            transitionToStage("blueprint");
        } catch {
            setGenerationError("Failed to retry generation. Please review blueprint and try again.");
            transitionToStage("blueprint");
        }
    };

    const sidebar = stage === "clarifying"
        ? (
            <WizardClarifier
                projectId={projectId}
                mode="synthesis"
                onComplete={onClarificationComplete}
                initialSessionId={stage === "clarifying" ? sessionId : null}
            />
        )
        : (
            <RunResumePanel
                projectId={project._id}
                activeRunId={project.activeRunId as Id<"generationRuns"> | undefined}
                showRetry={stage === "generation_failed"}
                onRetryGeneration={stage === "generation_failed" ? onRetryGeneration : undefined}
            />
        );

    return (
        <EditorLayout
            title={project.title}
            status={project.status}
            sidebar={sidebar}
            headerRight={
                <div className="flex items-center gap-3">
                    <EditorStageStepper stage={stage} className="hidden lg:flex" />
                    {project?._id && (
                        <RunSelector
                            projectId={project._id}
                            activeRunId={project.activeRunId as Id<"generationRuns"> | undefined}
                        />
                    )}
                </div>
            }
        >
            <AnimatePresence mode="wait">
                {isTransitioning && (
                    <motion.div
                        key="transition"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 z-50"
                    >
                        <StageTransitionLoader stage={stage} message={transitionMessage} />
                    </motion.div>
                )}

                {stage === "clarifying" && !isTransitioning && (
                    <motion.div
                        key="clarifying"
                        variants={stageVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        className="flex h-full w-full flex-col items-center justify-center text-center"
                    >
                        <div className="max-w-md space-y-4">
                            <h3 className="text-xl font-semibold text-white">Presentation Preview</h3>
                            <p className="text-sm text-neutral-400 mt-2">
                                The slide deck will appear here once the blueprint is ready.
                            </p>
                        </div>
                    </motion.div>
                )}

                {stage === "blueprint" && sessionId && !isTransitioning && (
                    <motion.div
                        key="blueprint"
                        variants={stageVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        className="h-full w-full"
                    >
                        <BlueprintReview sessionId={sessionId} onApprove={onBlueprintApproved} />
                    </motion.div>
                )}

                {stage === "generating" && sessionId && !isTransitioning && (
                    <motion.div
                        key="generating"
                        variants={stageVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        className="h-full w-full"
                    >
                        <GenerationProgress sessionId={sessionId} onComplete={onGenerationComplete} />
                    </motion.div>
                )}

                {stage === "generation_failed" && !isTransitioning && (
                    <motion.div
                        key="generation_failed"
                        variants={stageVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        className="flex h-full w-full items-center justify-center bg-neutral-950 p-6"
                    >
                        <div className="w-full max-w-lg rounded-xl border border-red-500/30 bg-red-500/5 p-6 text-center">
                            <AlertTriangle className="mx-auto h-8 w-8 text-red-400" />
                            <h3 className="mt-3 text-lg font-semibold text-white">Generation failed</h3>
                            <p className="mt-2 text-sm text-red-200/90">
                                {generationError || "The run did not complete successfully."}
                            </p>
                            <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
                                <Button
                                    variant="outline"
                                    className="border-neutral-700 text-neutral-200"
                                    onClick={() => setStage("blueprint")}
                                >
                                    Back to blueprint
                                </Button>
                                <Button className="bg-emerald-600 hover:bg-emerald-500" onClick={onRetryGeneration}>
                                    <RotateCcw className="mr-2 h-4 w-4" />
                                    Retry generation
                                </Button>
                            </div>
                        </div>
                    </motion.div>
                )}

                {stage === "completed" && sessionId && !isTransitioning && (
                    <motion.div
                        key="completed"
                        variants={stageVariants}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        className="h-full w-full"
                    >
                        <SlideViewer sessionId={sessionId} />
                    </motion.div>
                )}
            </AnimatePresence>
        </EditorLayout>
    );
}
