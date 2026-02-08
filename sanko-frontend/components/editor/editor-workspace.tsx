"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { WizardClarifier } from "./wizard-clarifier";
import { BlueprintReview } from "./blueprint-review";
import { GenerationProgress } from "./generation-progress";
import { SlideViewer } from "./slide-viewer";
import { EditorLayout } from "./editor-layout";
import { StageTransitionLoader } from "./stage-transition-loader";
import { useAuth } from "@/components/auth-provider";

type EditorStage = "clarifying" | "blueprint" | "generating" | "completed";

interface EditorWorkspaceProps {
    projectId: string;
}

// Animation variants for smooth stage transitions
const stageVariants = {
    initial: { opacity: 0, y: 20, scale: 0.98 },
    animate: {
        opacity: 1,
        y: 0,
        scale: 1,
        transition: { duration: 0.4, ease: "easeOut" as const }
    },
    exit: {
        opacity: 0,
        y: -20,
        scale: 0.98,
        transition: { duration: 0.3, ease: "easeIn" as const }
    }
};

export function EditorWorkspace({ projectId }: EditorWorkspaceProps) {
    const { user } = useAuth();
    const [stage, setStage] = useState<EditorStage>("clarifying");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [projectMode, setProjectMode] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const [isTransitioning, setIsTransitioning] = useState(false);
    const [transitionMessage, setTransitionMessage] = useState("");

    useEffect(() => {
        async function fetchProject() {
            if (!user || !projectId) return;

            try {
                const token = await user.getIdToken();
                const res = await fetch(`/api/projects/${projectId}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (res.ok) {
                    const data = await res.json();
                    setProjectMode(data.project.mode);
                } else {
                    console.error("Failed to fetch project");
                }
            } catch (error) {
                console.error("Error fetching project:", error);
            } finally {
                setLoading(false);
            }
        }

        fetchProject();
    }, [user, projectId]);

    if (loading) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-black">
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="flex flex-col items-center gap-4"
                >
                    <div className="relative w-16 h-16">
                        <motion.div
                            className="absolute inset-0 rounded-full border-2 border-neutral-800"
                        />
                        <motion.div
                            className="absolute inset-0 rounded-full border-2 border-transparent border-t-emerald-500"
                            animate={{ rotate: 360 }}
                            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                        />
                    </div>
                    <span className="text-neutral-400 text-sm">Loading project...</span>
                </motion.div>
            </div>
        );
    }

    // Smooth transition to next stage with loading animation
    const transitionToStage = (newStage: EditorStage, message?: string) => {
        setIsTransitioning(true);
        setTransitionMessage(message || "");

        // Brief transition animation
        setTimeout(() => {
            setStage(newStage);
            setIsTransitioning(false);
        }, 800);
    };

    // Passed to WizardClarifier to trigger state change
    const onClarificationComplete = (sid: string) => {
        setSessionId(sid);
        transitionToStage("blueprint", "Creating your presentation blueprint...");
    };

    // Passed to BlueprintReview
    const onBlueprintApproved = () => {
        transitionToStage("generating", "Starting AI generation...");
    };

    // Passed to GenerationProgress
    const onGenerationComplete = (result: Record<string, unknown>) => {
        transitionToStage("completed", "Finalizing your presentation...");
        console.log("Generation result:", result);
    };

    return (
        <EditorLayout
            sidebar={
                <WizardClarifier
                    projectId={projectId}
                    mode={projectMode || "synthesis"}
                    onComplete={onClarificationComplete}
                />
            }
        >
            <AnimatePresence mode="wait">
                {/* Transition loader overlay */}
                {isTransitioning && (
                    <motion.div
                        key="transition"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="absolute inset-0 z-50"
                    >
                        <StageTransitionLoader
                            stage={stage}
                            message={transitionMessage}
                        />
                    </motion.div>
                )}

                {/* Clarifying stage - placeholder preview */}
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
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: 0.2 }}
                            >
                                <h3 className="text-xl font-semibold text-white">Presentation Preview</h3>
                                <p className="text-sm text-neutral-400 mt-2">
                                    The slide deck will appear here once we&apos;ve composed the blueprint.
                                </p>
                            </motion.div>

                            {/* Animated placeholder */}
                            <motion.div
                                className="mt-6 p-6 rounded-xl border border-dashed border-neutral-800 bg-neutral-900/30"
                                initial={{ opacity: 0, scale: 0.95 }}
                                animate={{ opacity: 1, scale: 1 }}
                                transition={{ delay: 0.4 }}
                            >
                                <motion.div
                                    className="h-8 w-2/3 bg-neutral-800/50 rounded mb-4 mx-auto"
                                    animate={{ opacity: [0.5, 0.8, 0.5] }}
                                    transition={{ duration: 2, repeat: Infinity }}
                                />
                                <motion.div
                                    className="h-4 w-full bg-neutral-800/50 rounded mb-2"
                                    animate={{ opacity: [0.4, 0.7, 0.4] }}
                                    transition={{ duration: 2, repeat: Infinity, delay: 0.2 }}
                                />
                                <motion.div
                                    className="h-4 w-5/6 bg-neutral-800/50 rounded mb-2 mx-auto"
                                    animate={{ opacity: [0.3, 0.6, 0.3] }}
                                    transition={{ duration: 2, repeat: Infinity, delay: 0.4 }}
                                />
                                <motion.div
                                    className="h-4 w-4/5 bg-neutral-800/50 rounded mx-auto"
                                    animate={{ opacity: [0.3, 0.5, 0.3] }}
                                    transition={{ duration: 2, repeat: Infinity, delay: 0.6 }}
                                />
                            </motion.div>

                            {/* Helpful tips */}
                            <motion.p
                                className="text-xs text-neutral-600 mt-4"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: 0.8 }}
                            >
                                💡 Complete the wizard on the left to generate your outline
                            </motion.p>
                        </div>
                    </motion.div>
                )}

                {/* Blueprint review stage */}
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

                {/* Generation progress stage */}
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

                {/* Completed - slide viewer */}
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
