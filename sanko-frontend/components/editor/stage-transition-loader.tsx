"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface StageTransitionLoaderProps {
    stage: "clarifying" | "blueprint" | "generating" | "completed" | "generation_failed";
    message?: string;
}

const stageMessages: Record<string, { title: string; subtitle: string; icon: string }> = {
    clarifying: {
        title: "Setting up your presentation",
        subtitle: "Just a moment while we prepare...",
        icon: "*"
    },
    blueprint: {
        title: "Crafting your outline",
        subtitle: "AI is analyzing your requirements...",
        icon: "[]"
    },
    generating: {
        title: "Generating slides",
        subtitle: "Our AI agents are working on your presentation...",
        icon: "+"
    },
    completed: {
        title: "Almost there",
        subtitle: "Finalizing your presentation...",
        icon: "OK"
    },
    generation_failed: {
        title: "Generation failed",
        subtitle: "Preparing recovery options...",
        icon: "!"
    }
};

// Shimmer skeleton for loading states
export function ShimmerSkeleton({ className }: { className?: string }) {
    return (
        <div className={cn("relative overflow-hidden bg-neutral-800/50 rounded", className)}>
            <motion.div
                className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/5 to-transparent"
                animate={{ translateX: ["-100%", "100%"] }}
                transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
            />
        </div>
    );
}

// Blueprint skeleton placeholder
export function BlueprintSkeleton() {
    return (
        <div className="space-y-4 p-6 max-w-4xl mx-auto">
            {/* Title skeleton */}
            <div className="flex items-center gap-4 mb-8">
                <ShimmerSkeleton className="h-8 w-2/3" />
            </div>

            {/* Slide cards skeleton */}
            {[1, 2, 3, 4].map((i) => (
                <motion.div
                    key={i}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4"
                >
                    <div className="flex items-start gap-4">
                        <ShimmerSkeleton className="h-6 w-6 rounded" />
                        <ShimmerSkeleton className="h-6 w-6 rounded" />
                        <div className="flex-1 space-y-3">
                            <ShimmerSkeleton className="h-6 w-1/2" />
                            <ShimmerSkeleton className="h-16 w-full" />
                        </div>
                    </div>
                </motion.div>
            ))}
        </div>
    );
}

// Slide generation progress skeleton
export function GenerationSkeleton() {
    return (
        <div className="space-y-6 p-6 max-w-2xl mx-auto">
            {/* Progress header */}
            <div className="text-center space-y-4">
                <motion.div
                    className="mx-auto w-16 h-16 rounded-full bg-gradient-to-br from-emerald-500/20 to-cyan-500/20 flex items-center justify-center"
                    animate={{ scale: [1, 1.1, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                >
                    <motion.div
                        className="w-12 h-12 rounded-full border-2 border-emerald-500/50 border-t-emerald-500"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    />
                </motion.div>
                <ShimmerSkeleton className="h-6 w-48 mx-auto" />
                <ShimmerSkeleton className="h-4 w-32 mx-auto" />
            </div>

            {/* Agent cards skeleton */}
            {[1, 2, 3].map((i) => (
                <motion.div
                    key={i}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.15 }}
                    className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-4 flex items-center gap-4"
                >
                    <ShimmerSkeleton className="h-10 w-10 rounded-full" />
                    <div className="flex-1 space-y-2">
                        <ShimmerSkeleton className="h-4 w-24" />
                        <ShimmerSkeleton className="h-3 w-48" />
                    </div>
                </motion.div>
            ))}
        </div>
    );
}

// Main stage transition loader
export function StageTransitionLoader({ stage, message }: StageTransitionLoaderProps) {
    const stageInfo = stageMessages[stage];

    return (
        <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="flex h-full w-full flex-col items-center justify-center bg-neutral-950"
        >
            {/* Animated background orbs */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <motion.div
                    className="absolute top-1/4 left-1/4 w-64 h-64 rounded-full bg-emerald-500/5 blur-3xl"
                    animate={{
                        x: [0, 50, 0],
                        y: [0, 30, 0],
                        scale: [1, 1.2, 1]
                    }}
                    transition={{ duration: 8, repeat: Infinity }}
                />
                <motion.div
                    className="absolute bottom-1/4 right-1/4 w-48 h-48 rounded-full bg-cyan-500/5 blur-3xl"
                    animate={{
                        x: [0, -30, 0],
                        y: [0, -50, 0],
                        scale: [1.2, 1, 1.2]
                    }}
                    transition={{ duration: 6, repeat: Infinity }}
                />
            </div>

            {/* Content */}
            <div className="relative z-10 text-center space-y-6">
                {/* Animated icon */}
                <motion.div
                    className="text-5xl"
                    animate={{
                        y: [0, -10, 0],
                        rotate: [0, 5, -5, 0]
                    }}
                    transition={{ duration: 2, repeat: Infinity }}
                >
                    {stageInfo.icon}
                </motion.div>

                {/* Spinner */}
                <div className="relative w-20 h-20 mx-auto">
                    <motion.div
                        className="absolute inset-0 rounded-full border-2 border-neutral-800"
                    />
                    <motion.div
                        className="absolute inset-0 rounded-full border-2 border-transparent border-t-emerald-500"
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                    />
                    <motion.div
                        className="absolute inset-2 rounded-full border-2 border-transparent border-t-cyan-500"
                        animate={{ rotate: -360 }}
                        transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
                    />
                </div>

                {/* Text */}
                <div className="space-y-2">
                    <motion.h3
                        className="text-xl font-semibold text-white"
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                    >
                        {message || stageInfo.title}
                    </motion.h3>
                    <motion.p
                        className="text-sm text-neutral-400"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 0.2 }}
                    >
                        {stageInfo.subtitle}
                    </motion.p>
                </div>

                {/* Animated dots */}
                <div className="flex justify-center gap-2">
                    {[0, 1, 2].map((i) => (
                        <motion.div
                            key={i}
                            className="w-2 h-2 rounded-full bg-emerald-500"
                            animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1, 0.8] }}
                            transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                        />
                    ))}
                </div>
            </div>
        </motion.div>
    );
}

// AI thinking animation for chat/wizard
export function AIThinkingIndicator() {
    return (
        <div className="flex items-center gap-3 p-4 rounded-lg bg-neutral-900/50 border border-neutral-800">
            <div className="relative w-8 h-8">
                <motion.div
                    className="absolute inset-0 rounded-full bg-gradient-to-br from-emerald-500/20 to-cyan-500/20"
                    animate={{ scale: [1, 1.2, 1] }}
                    transition={{ duration: 1.5, repeat: Infinity }}
                />
                <motion.div
                    className="absolute inset-1 rounded-full border-2 border-emerald-500/50 border-t-emerald-500"
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                />
            </div>
            <div className="flex items-center gap-1">
                <span className="text-sm text-neutral-400">AI is thinking</span>
                {[0, 1, 2].map((i) => (
                    <motion.span
                        key={i}
                        className="text-emerald-500"
                        animate={{ opacity: [0, 1, 0] }}
                        transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                    >
                        .
                    </motion.span>
                ))}
            </div>
        </div>
    );
}
