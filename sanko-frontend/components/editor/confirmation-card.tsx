"use client";

import { motion } from "framer-motion";
import { Check, X, FileText, Users, Layers, Palette, MessageSquare, Quote, Layout } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface ConfirmationSummary {
    title: string;
    audience: string;
    slide_count: number;
    focus_areas: string[];
    emphasis_style: string;
    tone: string;
    citation_style: string;
    references_placement: string;
    theme: string;
    special_requests?: string;
    agent_decides_title?: boolean;
    agent_decides_theme?: boolean;
    agent_decides_citation?: boolean;
}

interface ConfirmationCardProps {
    summary: ConfirmationSummary;
    message?: string;
    onApprove: () => void;
    onEdit?: () => void;
    isLoading?: boolean;
}

export function ConfirmationCard({
    summary,
    message,
    onApprove,
    onEdit,
    isLoading = false
}: ConfirmationCardProps) {
    const items = [
        {
            icon: FileText,
            label: "Title/Topic",
            value: summary.agent_decides_title ? "(Auto-generated)" : summary.title,
            auto: summary.agent_decides_title
        },
        {
            icon: Users,
            label: "Audience",
            value: summary.audience
        },
        {
            icon: Layers,
            label: "Slides",
            value: `${summary.slide_count} slides`
        },
        {
            icon: MessageSquare,
            label: "Focus Areas",
            value: summary.focus_areas.join(", ") || "(General coverage)"
        },
        {
            icon: Palette,
            label: "Style",
            value: `${summary.emphasis_style} • ${summary.tone}`
        },
        {
            icon: Quote,
            label: "Citations",
            value: summary.agent_decides_citation
                ? "(Auto-selected)"
                : `${summary.citation_style.toUpperCase()} • ${summary.references_placement === "last_slide" ? "Last slide" : "Distributed"}`,
            auto: summary.agent_decides_citation
        },
        {
            icon: Layout,
            label: "Theme",
            value: summary.agent_decides_theme ? "(Auto-selected)" : summary.theme,
            auto: summary.agent_decides_theme
        }
    ];

    return (
        <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className="w-full max-w-xl mx-auto"
        >
            <div className="glass-card overflow-hidden border-emerald-500/20 shadow-[0_0_30px_rgba(16,185,129,0.1)]">
                {/* Header */}
                <div className="bg-gradient-to-r from-emerald-500/10 to-emerald-600/5 border-b border-emerald-500/20 px-5 py-4">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
                            <Check className="w-4 h-4 text-emerald-400" />
                        </div>
                        <div>
                            <h3 className="text-sm font-semibold text-white">Ready to Generate</h3>
                            <p className="text-xs text-neutral-400">
                                {message || "Please review your presentation requirements"}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Content */}
                <div className="p-5 space-y-3">
                    {items.map((item, index) => (
                        <motion.div
                            key={item.label}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.05 }}
                            className="flex items-start gap-3 group"
                        >
                            <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0 group-hover:border-emerald-500/30 transition-colors">
                                <item.icon className="w-3.5 h-3.5 text-neutral-400 group-hover:text-emerald-400 transition-colors" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <span className="text-[10px] uppercase tracking-wider text-neutral-500 font-medium">
                                    {item.label}
                                </span>
                                <p className={cn(
                                    "text-sm text-neutral-200 truncate",
                                    item.auto && "italic text-neutral-400"
                                )}>
                                    {item.value}
                                </p>
                            </div>
                        </motion.div>
                    ))}

                    {summary.special_requests && (
                        <motion.div
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: items.length * 0.05 }}
                            className="mt-4 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20"
                        >
                            <span className="text-[10px] uppercase tracking-wider text-amber-400 font-medium">
                                Special Requests
                            </span>
                            <p className="text-sm text-amber-200/80 mt-1">
                                {summary.special_requests}
                            </p>
                        </motion.div>
                    )}
                </div>

                {/* Actions */}
                <div className="border-t border-white/10 bg-white/[0.02] px-5 py-4 flex items-center justify-end gap-3">
                    {onEdit && (
                        <Button
                            variant="ghost"
                            size="sm"
                            onClick={onEdit}
                            disabled={isLoading}
                            className="text-neutral-400 hover:text-white hover:bg-white/10"
                        >
                            <X className="w-4 h-4 mr-2" />
                            Edit
                        </Button>
                    )}
                    <Button
                        size="sm"
                        onClick={onApprove}
                        disabled={isLoading}
                        className="bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white shadow-lg shadow-emerald-900/30 transition-all hover:shadow-emerald-900/50"
                    >
                        {isLoading ? (
                            <>
                                <motion.div
                                    animate={{ rotate: 360 }}
                                    transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                                    className="w-4 h-4 mr-2 border-2 border-white/30 border-t-white rounded-full"
                                />
                                Confirming...
                            </>
                        ) : (
                            <>
                                <Check className="w-4 h-4 mr-2" />
                                Approve & Continue
                            </>
                        )}
                    </Button>
                </div>
            </div>
        </motion.div>
    );
}
