"use client";

import { useState, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Check, MessageSquare, Send, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

export interface ChoiceOption {
    id: string;
    label: string;
    icon?: React.ReactNode;
    description?: string;
}

interface ChoiceQuestionCardProps {
    question: string;
    options: ChoiceOption[];
    onSelect: (optionId: string, customText?: string) => void;
    allowMultiple?: boolean;
    showCustomInput?: boolean;
    isLoading?: boolean;
    className?: string;
}

export function ChoiceQuestionCard({
    question,
    options,
    onSelect,
    allowMultiple = false,
    showCustomInput = true,
    isLoading = false,
    className,
}: ChoiceQuestionCardProps) {
    const [selectedOptions, setSelectedOptions] = useState<Set<string>>(new Set());
    const [showCustom, setShowCustom] = useState(false);
    const [customText, setCustomText] = useState("");

    const normalizedOptions = useMemo(() => {
        const seen = new Set<string>();
        const next: ChoiceOption[] = [];

        for (let index = 0; index < options.length; index += 1) {
            const option = options[index];
            const label =
                typeof option?.label === "string" && option.label.trim()
                    ? option.label.trim()
                    : typeof option?.id === "string" && option.id.trim()
                        ? option.id.trim()
                        : `Option ${index + 1}`;
            const id =
                typeof option?.id === "string" && option.id.trim()
                    ? option.id.trim()
                    : `option-${index + 1}-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`;

            if (seen.has(id)) continue;
            seen.add(id);
            next.push({
                ...option,
                id,
                label,
                description:
                    typeof option?.description === "string" && option.description.trim()
                        ? option.description.trim()
                        : undefined,
            });
        }

        return next;
    }, [options]);

    const handleOptionClick = useCallback((optionId: string) => {
        if (allowMultiple) {
            setSelectedOptions(prev => {
                const next = new Set(prev);
                if (next.has(optionId)) {
                    next.delete(optionId);
                } else {
                    next.add(optionId);
                }
                return next;
            });
        } else {
            // Single select - immediately submit
            onSelect(optionId);
        }
    }, [allowMultiple, onSelect]);

    const handleMultiSubmit = useCallback(() => {
        if (selectedOptions.size > 0) {
            onSelect(Array.from(selectedOptions).join(","));
        }
    }, [selectedOptions, onSelect]);

    const handleCustomSubmit = useCallback(() => {
        if (customText.trim()) {
            onSelect("custom", customText.trim());
            setCustomText("");
            setShowCustom(false);
        }
    }, [customText, onSelect]);

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleCustomSubmit();
        }
    };

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            className={cn("space-y-5", className)}
        >
            {/* Question Text */}
            <div className="flex items-start gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-emerald-500/10 border border-emerald-500/20">
                    <MessageSquare className="h-4 w-4 text-emerald-500" />
                </div>
                <div className="pt-0.5 text-base text-neutral-100 leading-relaxed">
                    <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                            p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                            ul: ({ children }) => <ul className="mb-2 list-disc pl-5 space-y-1">{children}</ul>,
                            ol: ({ children }) => <ol className="mb-2 list-decimal pl-5 space-y-1">{children}</ol>,
                            li: ({ children }) => <li className="text-neutral-100">{children}</li>,
                            strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                        }}
                    >
                        {question}
                    </ReactMarkdown>
                </div>
            </div>

            {/* Option Cards Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pl-11">
                <AnimatePresence mode="popLayout">
                    {normalizedOptions.map((option, index) => (
                        <motion.button
                            key={option.id}
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.95 }}
                            transition={{ delay: index * 0.05, duration: 0.2 }}
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            onClick={() => handleOptionClick(option.id)}
                            disabled={isLoading}
                            className={cn(
                                "group relative flex flex-col items-start gap-2 rounded-xl border p-4 text-left transition-all duration-200",
                                "bg-neutral-900/50 border-neutral-800 hover:border-emerald-500/50 hover:bg-neutral-900",
                                "focus:outline-none focus:ring-2 focus:ring-emerald-500/30 focus:ring-offset-2 focus:ring-offset-neutral-950",
                                selectedOptions.has(option.id) && "border-emerald-500 bg-emerald-500/10",
                                isLoading && "opacity-50 cursor-not-allowed"
                            )}
                        >
                            {/* Selection indicator */}
                            {allowMultiple && (
                                <div className={cn(
                                    "absolute top-3 right-3 h-5 w-5 rounded-md border-2 transition-all",
                                    selectedOptions.has(option.id)
                                        ? "bg-emerald-500 border-emerald-500"
                                        : "border-neutral-700 group-hover:border-neutral-500"
                                )}>
                                    {selectedOptions.has(option.id) && (
                                        <Check className="h-full w-full text-white p-0.5" />
                                    )}
                                </div>
                            )}

                            {/* Icon */}
                            {option.icon && (
                                <div className="text-2xl">{option.icon}</div>
                            )}

                            {/* Label */}
                            <span className={cn(
                                "font-medium text-sm transition-colors",
                                selectedOptions.has(option.id)
                                    ? "text-emerald-400"
                                    : "text-neutral-200 group-hover:text-white"
                            )}>
                                {option.label}
                            </span>

                            {/* Description */}
                            {option.description && (
                                <span className="text-xs text-neutral-500 leading-relaxed">
                                    {option.description}
                                </span>
                            )}
                        </motion.button>
                    ))}
                </AnimatePresence>
            </div>

            {/* Multi-select submit button */}
            {allowMultiple && selectedOptions.size > 0 && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="pl-11"
                >
                    <Button
                        onClick={handleMultiSubmit}
                        disabled={isLoading}
                        className="bg-emerald-600 hover:bg-emerald-500 text-white"
                    >
                        {isLoading ? (
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                        ) : (
                            <Check className="h-4 w-4 mr-2" />
                        )}
                        Continue with {selectedOptions.size} selected
                    </Button>
                </motion.div>
            )}

            {/* Custom Input Toggle + Field */}
            {showCustomInput && (
                <div className="pl-11">
                    <AnimatePresence mode="wait">
                        {!showCustom ? (
                            <motion.button
                                key="toggle"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                exit={{ opacity: 0 }}
                                onClick={() => setShowCustom(true)}
                                className="text-sm text-neutral-500 hover:text-emerald-400 transition-colors flex items-center gap-2"
                            >
                                <MessageSquare className="h-3.5 w-3.5" />
                                Or type your own answer...
                            </motion.button>
                        ) : (
                            <motion.div
                                key="input"
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: "auto" }}
                                exit={{ opacity: 0, height: 0 }}
                                className="space-y-3"
                            >
                                <div className="relative">
                                    <Textarea
                                        value={customText}
                                        onChange={(e) => setCustomText(e.target.value)}
                                        onKeyDown={handleKeyDown}
                                        placeholder="Type your custom answer..."
                                        className="min-h-[80px] bg-neutral-900/50 border-neutral-800 text-neutral-200 placeholder:text-neutral-600 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 resize-none pr-12"
                                        autoFocus
                                    />
                                    <Button
                                        size="icon"
                                        onClick={handleCustomSubmit}
                                        disabled={!customText.trim() || isLoading}
                                        className={cn(
                                            "absolute bottom-2 right-2 h-8 w-8 rounded-lg transition-all",
                                            customText.trim()
                                                ? "bg-emerald-600 hover:bg-emerald-500 text-white"
                                                : "bg-neutral-800 text-neutral-500 cursor-not-allowed"
                                        )}
                                    >
                                        {isLoading ? (
                                            <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                            <Send className="h-4 w-4" />
                                        )}
                                    </Button>
                                </div>
                                <button
                                    onClick={() => {
                                        setShowCustom(false);
                                        setCustomText("");
                                    }}
                                    className="text-xs text-neutral-500 hover:text-neutral-400 transition-colors"
                                >
                                    Cancel
                                </button>
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            )}
        </motion.div>
    );
}

// Compact version for inline use
export function ChoiceQuestionInline({
    options,
    onSelect,
    className,
}: {
    options: ChoiceOption[];
    onSelect: (optionId: string) => void;
    className?: string;
}) {
    return (
        <div className={cn("flex flex-wrap gap-2", className)}>
            {options.map((option) => (
                <motion.button
                    key={option.id}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => onSelect(option.id)}
                    className={cn(
                        "inline-flex items-center gap-2 px-4 py-2 rounded-full text-sm font-medium transition-all",
                        "bg-neutral-800/50 border border-neutral-700 text-neutral-300",
                        "hover:border-emerald-500/50 hover:bg-neutral-800 hover:text-white",
                        "focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                    )}
                >
                    {option.icon && <span className="text-base">{option.icon}</span>}
                    {option.label}
                </motion.button>
            ))}
        </div>
    );
}
