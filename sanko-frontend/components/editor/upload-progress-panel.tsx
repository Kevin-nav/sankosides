"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, Check, Loader2, Clock, Sparkles, AlertCircle, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { ChoiceQuestionInline, ChoiceOption } from "./choice-question-card";

export interface UploadStage {
    id: string;
    label: string;
    status: "pending" | "active" | "completed" | "error";
    estimatedSeconds?: number;
}

interface UploadProgressPanelProps {
    fileName: string;
    fileSize: string;
    stages: UploadStage[];
    currentProgress: number; // 0-100
    estimatedSecondsRemaining?: number;
    onCancel?: () => void;
    // Parallel question while waiting
    parallelQuestion?: {
        question: string;
        options: ChoiceOption[];
        onSelect: (optionId: string) => void;
    };
    className?: string;
}

export function UploadProgressPanel({
    fileName,
    fileSize,
    stages,
    currentProgress,
    estimatedSecondsRemaining,
    onCancel,
    parallelQuestion,
    className,
}: UploadProgressPanelProps) {
    const [showParallelQuestion, setShowParallelQuestion] = useState(false);

    // Show parallel question after a short delay to feel natural
    useEffect(() => {
        if (parallelQuestion && currentProgress > 10 && currentProgress < 90) {
            const timer = setTimeout(() => setShowParallelQuestion(true), 1500);
            return () => clearTimeout(timer);
        }
    }, [parallelQuestion, currentProgress]);

    const formatTime = (seconds: number) => {
        if (seconds < 60) return `~${seconds}s left`;
        return `~${Math.ceil(seconds / 60)}min left`;
    };

    const getStageIcon = (status: UploadStage["status"]) => {
        switch (status) {
            case "completed":
                return <Check className="h-3.5 w-3.5 text-emerald-500" />;
            case "active":
                return <Loader2 className="h-3.5 w-3.5 text-emerald-400 animate-spin" />;
            case "error":
                return <AlertCircle className="h-3.5 w-3.5 text-red-500" />;
            default:
                return <div className="h-2.5 w-2.5 rounded-full bg-neutral-700" />;
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className={cn(
                "rounded-xl border border-neutral-800 bg-neutral-900/80 backdrop-blur-sm overflow-hidden",
                className
            )}
        >
            {/* File Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-neutral-800/50 bg-neutral-900/50">
                <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                        <FileText className="h-5 w-5 text-emerald-500" />
                    </div>
                    <div>
                        <p className="font-medium text-sm text-white truncate max-w-[200px]">
                            {fileName}
                        </p>
                        <p className="text-xs text-neutral-500">{fileSize}</p>
                    </div>
                </div>
                {onCancel && (
                    <button
                        onClick={onCancel}
                        className="p-1.5 rounded-md hover:bg-neutral-800 text-neutral-500 hover:text-neutral-300 transition-colors"
                    >
                        <X className="h-4 w-4" />
                    </button>
                )}
            </div>

            {/* Progress Bar */}
            <div className="px-4 py-4">
                <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-neutral-400">Processing document...</span>
                    <div className="flex items-center gap-2">
                        {estimatedSecondsRemaining && estimatedSecondsRemaining > 0 && (
                            <span className="flex items-center gap-1 text-xs text-neutral-500">
                                <Clock className="h-3 w-3" />
                                {formatTime(estimatedSecondsRemaining)}
                            </span>
                        )}
                        <span className="text-xs font-mono text-emerald-400">
                            {Math.round(currentProgress)}%
                        </span>
                    </div>
                </div>

                {/* Progress bar track */}
                <div className="h-2 bg-neutral-800 rounded-full overflow-hidden">
                    <motion.div
                        className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${currentProgress}%` }}
                        transition={{ duration: 0.3, ease: "easeOut" }}
                    />
                </div>

                {/* Stage Indicators */}
                <div className="mt-4 space-y-2">
                    {stages.map((stage, index) => (
                        <motion.div
                            key={stage.id}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.1 }}
                            className={cn(
                                "flex items-center gap-2.5 text-xs transition-colors",
                                stage.status === "completed" && "text-emerald-500",
                                stage.status === "active" && "text-white",
                                stage.status === "pending" && "text-neutral-600",
                                stage.status === "error" && "text-red-400"
                            )}
                        >
                            <div className="flex items-center justify-center w-5">
                                {getStageIcon(stage.status)}
                            </div>
                            <span className={cn(
                                "font-medium",
                                stage.status === "active" && "animate-pulse"
                            )}>
                                {stage.label}
                            </span>
                            {stage.status === "active" && stage.estimatedSeconds && (
                                <span className="text-neutral-500 ml-auto">
                                    {formatTime(stage.estimatedSeconds)}
                                </span>
                            )}
                        </motion.div>
                    ))}
                </div>
            </div>

            {/* Parallel Question - Asked while processing */}
            <AnimatePresence>
                {showParallelQuestion && parallelQuestion && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="border-t border-neutral-800/50"
                    >
                        <div className="px-4 py-4 bg-gradient-to-b from-emerald-500/5 to-transparent">
                            <div className="flex items-center gap-2 mb-3">
                                <Sparkles className="h-4 w-4 text-emerald-400" />
                                <span className="text-sm font-medium text-emerald-400">
                                    While you wait
                                </span>
                            </div>
                            <p className="text-sm text-neutral-300 mb-3">
                                {parallelQuestion.question}
                            </p>
                            <ChoiceQuestionInline
                                options={parallelQuestion.options}
                                onSelect={(id) => {
                                    parallelQuestion.onSelect(id);
                                    setShowParallelQuestion(false);
                                }}
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </motion.div>
    );
}

// Hook for managing upload progress state
export function useUploadProgress() {
    const [stages, setStages] = useState<UploadStage[]>([
        { id: "upload", label: "Uploading file", status: "pending" },
        { id: "extract", label: "Extracting content", status: "pending" },
        { id: "analyze", label: "Analyzing structure", status: "pending" },
        { id: "knowledge", label: "Building knowledge base", status: "pending" },
    ]);
    const [progress, setProgress] = useState(0);
    const [eta, setEta] = useState<number | undefined>();

    const updateFromSSE = (event: { stage: string; percent: number; eta_seconds?: number }) => {
        setProgress(event.percent);
        setEta(event.eta_seconds);

        setStages(prev => prev.map(s => {
            if (s.id === event.stage) {
                return { ...s, status: "active", estimatedSeconds: event.eta_seconds };
            }
            // Mark previous stages as complete
            const currentIndex = prev.findIndex(p => p.id === event.stage);
            const thisIndex = prev.findIndex(p => p.id === s.id);
            if (thisIndex < currentIndex) {
                return { ...s, status: "completed" };
            }
            return s;
        }));
    };

    const markComplete = () => {
        setProgress(100);
        setStages(prev => prev.map(s => ({ ...s, status: "completed" })));
    };

    const markError = (stageId: string) => {
        setStages(prev => prev.map(s =>
            s.id === stageId ? { ...s, status: "error" } : s
        ));
    };

    const reset = () => {
        setProgress(0);
        setEta(undefined);
        setStages(prev => prev.map(s => ({ ...s, status: "pending" })));
    };

    return {
        stages,
        progress,
        eta,
        updateFromSSE,
        markComplete,
        markError,
        reset,
    };
}
