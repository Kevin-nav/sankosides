"use client";

import { motion } from "framer-motion";
import { Image, FileText, Globe, ArrowRight, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";

interface ModeSelectorProps {
    onSelect: (mode: "replica" | "synthesis" | "research") => void;
}

const modes = [
    {
        id: "replica",
        title: "Replica Engine",
        description: "Recreate an existing slide from an image with pixel-perfect accuracy.",
        icon: Image,
        color: "from-blue-500 to-cyan-400",
        badge: "Visual Match",
    },
    {
        id: "synthesis",
        title: "Synthesis Engine",
        description: "Upload PDFs, notes, or docs to generate structured slides.",
        icon: FileText,
        color: "from-emerald-500 to-green-400",
        badge: "Most Popular",
    },
    {
        id: "research",
        title: "Deep Research",
        description: "Enter a topic and let AI research and build the presentation.",
        icon: Globe,
        color: "from-purple-500 to-pink-400",
        badge: "AI Agent",
    },
];

export function ModeSelector({ onSelect }: ModeSelectorProps) {
    return (
        <div className="flex flex-col gap-4">
            {modes.map((mode, index) => (
                <motion.div
                    key={mode.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1, duration: 0.4 }}
                    whileHover={{ scale: 1.02 }}
                    onClick={() => onSelect(mode.id as any)}
                    className="group relative cursor-pointer overflow-hidden rounded-xl border border-neutral-800/80 bg-neutral-900 p-5 shadow-md shadow-black/40 transition-all hover:border-emerald-500/50 hover:shadow-[0_4px_30px_-10px_rgba(16,185,129,0.3)]"
                >
                    {/* Subtle gradient background on hover */}
                    <div
                        className={cn(
                            "absolute inset-0 opacity-0 transition-opacity duration-500 group-hover:opacity-10 bg-gradient-to-br",
                            mode.color
                        )}
                    />

                    <div className="relative z-10 flex flex-col space-y-4">
                        <div className="flex items-center justify-between">
                            <div
                                className={cn(
                                    "flex h-12 w-12 items-center justify-center rounded-lg shadow-lg border border-white/10",
                                    "bg-neutral-900 group-hover:bg-neutral-800 transition-colors"
                                )}
                            >
                                <mode.icon className={cn("h-6 w-6 transition-colors", "text-emerald-500 group-hover:text-emerald-400")} />
                            </div>
                            {mode.id === "synthesis" && (
                                <span className="inline-flex items-center rounded-md bg-emerald-500/10 px-2.5 py-1 text-xs font-semibold text-emerald-400 border border-emerald-500/20 shadow-[0_0_10px_-4px_rgba(16,185,129,0.5)]">
                                    <Sparkles className="mr-1 h-3 w-3" />
                                    Popular
                                </span>
                            )}
                        </div>

                        <div className="space-y-3">
                            <h3 className="text-xl font-bold text-white transition-colors group-hover:text-emerald-400">
                                {mode.title}
                            </h3>
                            <p className="text-sm text-neutral-400 leading-relaxed font-medium group-hover:text-neutral-300 transition-colors">
                                {mode.description}
                            </p>
                        </div>

                        <div className="pt-4 mt-auto">
                            <span className="flex items-center text-sm font-semibold text-neutral-500 group-hover:text-white transition-colors">
                                Select Mode <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                            </span>
                        </div>
                    </div>
                </motion.div>
            ))}
        </div>
    );
}
