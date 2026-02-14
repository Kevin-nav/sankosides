"use client";

import { useState, useEffect, useCallback } from "react";
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Check, GripVertical, Plus, Trash2, Send, Wand2, AlertCircle, Loader2, ArrowUp, ArrowDown } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { cn } from "@/lib/utils";
import { useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";

interface SlideSkeleton {
    _localId?: string;
    order: number;
    title: string;
    content_type: string;
    // content_description replaces bullet_points for the review phase as per user request
    content_description?: string;
    bullet_points: string[]; // Keep for compatibility, but UI focuses on description
    needs_citation: boolean;
    needs_diagram: boolean;
    [key: string]: unknown; // Allow other props
}

interface FullSkeleton {
    presentation_title: string;
    target_audience: string;
    narrative_arc: string;
    slides: SlideSkeleton[];
    source_documents: string[];
    [key: string]: unknown;
}

interface BlueprintReviewProps {
    sessionId: string;
    onApprove: () => void;
}

export function BlueprintReview({ sessionId, onApprove }: BlueprintReviewProps) {
    const { user } = useAuth();
    const [skeleton, setSkeleton] = useState<FullSkeleton | null>(null);
    const [loading, setLoading] = useState(true);
    const [aiInput, setAiInput] = useState("");
    const [aiLoading, setAiLoading] = useState(false);
    const [approveLoading, setApproveLoading] = useState(false);
    const [generateLoading, setGenerateLoading] = useState(false);
    const [actionError, setActionError] = useState<string | null>(null);
    const [loadError, setLoadError] = useState<string | null>(null);
    const [outlineApproved, setOutlineApproved] = useState(false);

    const [loadingMessage, setLoadingMessage] = useState("Loading blueprint...");

    // Real-time progress from Convex
    const progress = useQuery(api.generation.getProgressBySession, { sessionId: sessionId || "" });

    // Effect to handle Convex updates
    useEffect(() => {
        if (progress?.blueprint) {
            console.log("Blueprint received via Convex:", progress.blueprint);
            processSkeleton(progress.blueprint);
            setLoading(false);
            return;
        }

        if (progress?.message) {
            setLoadingMessage(progress.message);
        }

    }, [progress]);

    const loadBlueprint = useCallback(async () => {
        if (!user) return;
        setLoadError(null);
        const token = await user.getIdToken();
        const res = await fetch(`/api/generate/blueprint/${sessionId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            if (data.skeleton) {
                processSkeleton(data.skeleton);
                setLoading(false);
            }
        } else {
            const err = await res.json().catch(() => ({}));
            setLoadError(err.detail || "Blueprint is not ready yet.");
            setLoading(false);
        }
    }, [sessionId, user]);

    // Initial load fallback (for existing sessions or direct link access)
    useEffect(() => {
        if (!sessionId || !user || skeleton) return;
        loadBlueprint();
    }, [sessionId, user, skeleton, loadBlueprint]);

    // Polling and SSE removed - replaced by Convex subscription

    function processSkeleton(skeletonData: Record<string, unknown>) {
        const rawSlides = (Array.isArray(skeletonData.slides) ? skeletonData.slides : []) as Array<Record<string, unknown>>;
        const slides = rawSlides.map((s) => ({
            _localId: typeof s._localId === "string" ? s._localId : `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`,
            ...s,
            content_description:
                (typeof s.content_description === "string" ? s.content_description : undefined) ||
                (Array.isArray(s.key_points) ? String(s.key_points[0] ?? "") : undefined) ||
                (typeof s.description === "string" ? s.description : undefined) ||
                "No description provided.",
        })) as SlideSkeleton[];

        setSkeleton({
            ...skeletonData,
            presentation_title: typeof skeletonData.presentation_title === "string" ? skeletonData.presentation_title : "Untitled Presentation",
            target_audience: typeof skeletonData.target_audience === "string" ? skeletonData.target_audience : "General Audience",
            narrative_arc: typeof skeletonData.narrative_arc === "string" ? skeletonData.narrative_arc : "",
            source_documents: Array.isArray(skeletonData.source_documents) ? (skeletonData.source_documents as string[]) : [],
            slides,
        } as FullSkeleton);
    }

    // startSSE removed

    const onDragEnd = (result: DropResult) => {
        if (!result.destination || !skeleton) return;
        const items = Array.from(skeleton.slides);
        const [reorderedItem] = items.splice(result.source.index, 1);
        items.splice(result.destination.index, 0, reorderedItem);
        // Update order property
        const updated = items.map((slide, index) => ({ ...slide, order: index + 1 }));
        setSkeleton({ ...skeleton, slides: updated });
        setOutlineApproved(false);
    };

    const handleAiRevision = async () => {
        if (!aiInput.trim() || !user) return;
        setAiLoading(true);
        setActionError(null);
        try {
            const token = await user.getIdToken();
            const res = await fetch(`/api/generate/clarify/${sessionId}`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ message: aiInput }) // User request for revision
            });

            if (res.ok) {
                await loadBlueprint(); // Reload updated blueprint
                setAiInput("");
            } else {
                const err = await res.json().catch(() => ({}));
                setActionError(err.detail || "Failed to apply AI revision.");
            }
        } catch (e) {
            console.error(e);
            setActionError("Failed to apply AI revision.");
        } finally {
            setAiLoading(false);
        }
    };

    const handleApproveOutline = async () => {
        if (!user || !skeleton || approveLoading) return;
        setApproveLoading(true);
        setActionError(null);
        try {
            const token = await user.getIdToken();

            const approveRes = await fetch(`/api/generate/blueprint/${sessionId}`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    approved: true,
                    modified_skeleton: skeleton
                })
            });

            if (!approveRes.ok) {
                const detail = await approveRes.text();
                setActionError(`Approval failed: ${detail}`);
                return;
            }
            setOutlineApproved(true);
        } catch (e) {
            console.error(e);
            setActionError("Failed to approve blueprint. Please try again.");
        } finally {
            setApproveLoading(false);
        }
    };

    const handleGenerate = async () => {
        if (!user || !sessionId || generateLoading) return;
        setGenerateLoading(true);
        setActionError(null);

        try {
            // Enforce two-step: require explicit approval first.
            if (!outlineApproved) {
                setActionError("Please approve the outline before starting generation.");
                return;
            }

            const token = await user.getIdToken();
            const generateRes = await fetch(`/api/generate/generate/${sessionId}`, {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json"
                }
            });

            if (!generateRes.ok) {
                const detail = await generateRes.text();
                setActionError(`Generation start failed: ${detail}`);
                return;
            }

            onApprove();
        } catch (e) {
            console.error(e);
            setActionError("Failed to start generation. Please try again.");
        } finally {
            setGenerateLoading(false);
        }
    };

    if (loading) return (
        <div className="flex h-full flex-col bg-neutral-950 p-6 text-white max-w-5xl mx-auto w-full">
            {/* Header skeleton */}
            <div className="mb-6 flex items-center justify-between py-4 border-b border-white/5">
                <div className="space-y-2">
                    <div className="h-7 w-48 bg-neutral-800/50 rounded animate-pulse" />
                    <div className="h-4 w-64 bg-neutral-800/30 rounded animate-pulse" />
                </div>
                <div className="h-10 w-36 bg-neutral-800/50 rounded animate-pulse" />
            </div>

            {/* Content skeleton */}
            <div className="flex-1 overflow-hidden flex gap-6">
                <div className="flex-1 space-y-4">
                    {[1, 2, 3, 4].map((i) => (
                        <div
                            key={i}
                            className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-4"
                            style={{ animationDelay: `${i * 100}ms` }}
                        >
                            <div className="flex items-start gap-4">
                                <div className="h-6 w-6 bg-neutral-800/50 rounded animate-pulse" />
                                <div className="h-6 w-6 bg-neutral-800/50 rounded animate-pulse" />
                                <div className="flex-1 space-y-3">
                                    <div className="h-6 w-1/2 bg-neutral-800/50 rounded animate-pulse" />
                                    <div className="h-16 w-full bg-neutral-800/30 rounded animate-pulse" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* Sidebar skeleton */}
                <div className="w-80 border-l border-white/5 pl-6">
                    <div className="h-4 w-24 bg-neutral-800/50 rounded animate-pulse mb-4" />
                    <div className="h-3 w-48 bg-neutral-800/30 rounded animate-pulse mb-6" />
                    <div className="h-32 w-full bg-neutral-900/30 rounded-xl border border-white/5 animate-pulse" />
                </div>
            </div>

            {/* Status message */}
            <div className="absolute bottom-8 left-1/2 -translate-x-1/2 flex items-center gap-3 bg-neutral-900/80 backdrop-blur-sm px-4 py-2 rounded-full border border-neutral-800">
                <div className="w-4 h-4 border-2 border-emerald-500/30 border-t-emerald-500 rounded-full animate-spin" />
                <span className="font-mono text-xs tracking-wider text-neutral-400 uppercase">{loadingMessage}</span>
            </div>
        </div>
    );
    if (!skeleton) return (
        <div className="flex h-full w-full items-center justify-center p-8">
            <div className="rounded-xl border border-red-500/30 bg-red-500/5 p-6 text-center">
                <p className="text-red-300">Failed to load blueprint.</p>
                <Button
                    variant="outline"
                    className="mt-3 border-neutral-700 text-neutral-200"
                    onClick={() => {
                        setLoading(true);
                        void loadBlueprint();
                    }}
                >
                    Retry
                </Button>
            </div>
        </div>
    );

    return (
        <div className="flex h-full flex-col bg-neutral-950 p-6 text-white max-w-5xl mx-auto w-full">
            <div className="mb-6 flex items-center justify-between sticky top-0 bg-neutral-950/80 backdrop-blur-md z-10 py-4 border-b border-white/5">
                <div>
                    <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
                        {skeleton.presentation_title || "Review Structure"}
                    </h2>
                    <p className="text-neutral-400 text-sm mt-1">
                        Refine the outline. Drag to reorder, edit titles, or ask AI to make changes.
                    </p>
                </div>
                <div className="flex gap-4">
                    <Button
                        onClick={handleApproveOutline}
                        disabled={approveLoading}
                        aria-label="Approve outline"
                        className="bg-neutral-900 hover:bg-neutral-800 text-white border border-neutral-800"
                    >
                        {approveLoading ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                            <Check className="mr-2 h-4 w-4" />
                        )}
                        {outlineApproved ? "Outline approved" : "Approve outline"}
                    </Button>

                    <Button
                        onClick={handleGenerate}
                        disabled={generateLoading || !outlineApproved}
                        aria-label="Start generation"
                        className="bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/20 shadow-lg disabled:opacity-60"
                    >
                        {generateLoading ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                            <Send className="mr-2 h-4 w-4" />
                        )}
                        {generateLoading ? "Starting..." : "Generate slides"}
                    </Button>
                </div>
            </div>
            {(actionError || loadError) && (
                <div className="mb-3 flex items-start gap-2 rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
                    <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                    <span>{actionError || loadError}</span>
                </div>
            )}

            <div className="flex-1 overflow-hidden flex gap-6">
                {/* Visual Outline (Drag & Drop) */}
                <div className="flex-1 overflow-y-auto custom-scrollbar pr-2">
                    <DragDropContext onDragEnd={onDragEnd}>
                        <Droppable droppableId="slides">
                            {(provided) => (
                                <div {...provided.droppableProps} ref={provided.innerRef} className="space-y-4 pb-20">
                                    {skeleton.slides.map((slide, idx) => (
                                        <Draggable key={slide._localId || `${slide.order}-${idx}`} draggableId={slide._localId || `${slide.order}-${idx}`} index={idx}>
                                            {(provided, snapshot) => (
                                                <div
                                                    ref={provided.innerRef}
                                                    {...provided.draggableProps}
                                                    className={cn(
                                                        "group relative rounded-xl border border-neutral-800 bg-neutral-900/50 p-4 hover:border-emerald-500/30 transition-all",
                                                        snapshot.isDragging && "border-emerald-500 shadow-xl shadow-emerald-500/10 z-50 bg-neutral-900"
                                                    )}
                                                >
                                                    <div className="flex items-start gap-4">
                                                        <div {...provided.dragHandleProps} className="mt-1 flex h-6 w-6 cursor-grab items-center justify-center rounded text-neutral-600 hover:text-emerald-400 active:cursor-grabbing" aria-label="Drag to reorder slide">
                                                            <GripVertical className="h-5 w-5" />
                                                        </div>
                                                        <div className="mt-0.5 flex flex-col gap-1">
                                                            <Button
                                                                type="button"
                                                                variant="ghost"
                                                                size="icon"
                                                                aria-label={`Move slide ${idx + 1} up`}
                                                                disabled={idx === 0}
                                                                className="h-5 w-5 text-neutral-500 hover:text-white"
                                                                onClick={() => {
                                                                    if (idx === 0) return;
                                                                    const reordered = [...skeleton.slides];
                                                                    [reordered[idx - 1], reordered[idx]] = [reordered[idx], reordered[idx - 1]];
                                                                    setSkeleton({
                                                                        ...skeleton,
                                                                        slides: reordered.map((slideItem, orderIndex) => ({ ...slideItem, order: orderIndex + 1 })),
                                                                    });
                                                                }}
                                                            >
                                                                <ArrowUp className="h-3 w-3" />
                                                            </Button>
                                                            <Button
                                                                type="button"
                                                                variant="ghost"
                                                                size="icon"
                                                                aria-label={`Move slide ${idx + 1} down`}
                                                                disabled={idx === skeleton.slides.length - 1}
                                                                className="h-5 w-5 text-neutral-500 hover:text-white"
                                                                onClick={() => {
                                                                    if (idx >= skeleton.slides.length - 1) return;
                                                                    const reordered = [...skeleton.slides];
                                                                    [reordered[idx + 1], reordered[idx]] = [reordered[idx], reordered[idx + 1]];
                                                                    setSkeleton({
                                                                        ...skeleton,
                                                                        slides: reordered.map((slideItem, orderIndex) => ({ ...slideItem, order: orderIndex + 1 })),
                                                                    });
                                                                }}
                                                            >
                                                                <ArrowDown className="h-3 w-3" />
                                                            </Button>
                                                        </div>
                                                        <div className="flex h-6 w-6 items-center justify-center rounded bg-neutral-800 text-xs font-medium text-neutral-400">
                                                            {idx + 1}
                                                        </div>

                                                        <div className="flex-1 space-y-3">
                                                            {/* Slide Title */}
                                                            <Input
                                                                value={slide.title}
                                                                onChange={(e) => {
                                                                    const newSlides = [...skeleton.slides];
                                                                    newSlides[idx].title = e.target.value;
                                                                    setSkeleton({ ...skeleton, slides: newSlides });
                                                                    setOutlineApproved(false);
                                                                }}
                                                                className="h-8 border-transparent bg-transparent p-0 text-lg font-semibold text-white focus-visible:ring-0 placeholder:text-neutral-600"
                                                                placeholder="Slide Title (e.g., Introduction)"
                                                            />

                                                            {/* Single Sentence Description */}
                                                            <Textarea
                                                                value={slide.content_description}
                                                                onChange={(e) => {
                                                                    const newSlides = [...skeleton.slides];
                                                                    newSlides[idx].content_description = e.target.value;
                                                                    setSkeleton({ ...skeleton, slides: newSlides });
                                                                    setOutlineApproved(false);
                                                                }}
                                                                className="min-h-[60px] resize-none border-transparent bg-neutral-950/30 p-2 text-sm text-neutral-300 focus:bg-neutral-950 focus:ring-1 focus:ring-emerald-500/50"
                                                                placeholder="Briefly describe what goes on this slide..."
                                                            />
                                                        </div>

                                                        <Button variant="ghost" size="icon" aria-label={`Remove slide ${idx + 1}`} className="text-neutral-600 hover:text-red-400 hover:bg-red-500/10"
                                                            onClick={() => {
                                                                const newSlides = skeleton.slides.filter((_, i) => i !== idx);
                                                                setSkeleton({ ...skeleton, slides: newSlides });
                                                                setOutlineApproved(false);
                                                            }}
                                                        >
                                                            <Trash2 className="h-4 w-4" />
                                                        </Button>
                                                    </div>
                                                </div>
                                            )}
                                        </Draggable>
                                    ))}
                                    {provided.placeholder}

                                    <Button
                                        variant="outline"
                                        aria-label="Add slide"
                                        className="w-full border-dashed border-neutral-800 text-neutral-500 hover:text-emerald-400 hover:border-emerald-500/50 hover:bg-emerald-500/5 py-8"
                                        onClick={() => {
                                            const newSlides = [...skeleton.slides, {
                                                _localId: `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
                                                order: skeleton.slides.length + 1,
                                                title: "New Slide",
                                                content_type: "body",
                                                content_description: "New slide description.",
                                                bullet_points: [],
                                                needs_citation: false,
                                                needs_diagram: false
                                            }];
                                            setSkeleton({ ...skeleton, slides: newSlides });
                                            setOutlineApproved(false);
                                        }}
                                    >
                                        <Plus className="mr-2 h-4 w-4" /> Add Slide
                                    </Button>
                                </div>
                            )}
                        </Droppable>
                    </DragDropContext>
                </div>

                {/* AI Revision Sidebar */}
                <div className="w-80 border-l border-white/5 pl-6 flex flex-col">
                    <div className="mb-4">
                        <h3 className="text-sm font-medium text-neutral-400 uppercase tracking-wider mb-2">Modify with AI</h3>
                        <p className="text-xs text-neutral-500">
                            Chat to add/remove slides, change the tone, or restructure the flow.
                        </p>
                    </div>

                    <div className="flex-1 bg-neutral-900/20 rounded-xl border border-white/5 p-4 mb-4 relative overflow-hidden">
                        {/* Placeholder for history - in this simplified view we just show the input logic */}
                        <div className="absolute inset-0 flex items-center justify-center text-neutral-700 opacity-20 pointer-events-none">
                            <Wand2 className="w-24 h-24" />
                        </div>
                    </div>

                    <div className="relative">
                        <Textarea
                            placeholder="Example: 'Add a slide about Ethics after slide 3' or 'Make it more formal'"
                            className="bg-neutral-900 border-neutral-800 min-h-[100px] resize-none pr-10 text-sm focus:border-emerald-500/50"
                            value={aiInput}
                            onChange={(e) => setAiInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault();
                                    handleAiRevision();
                                }
                            }}
                        />
                        <Button
                            size="icon"
                            className={cn("absolute bottom-3 right-3 h-8 w-8 rounded-full", aiLoading ? "bg-neutral-700 cursor-not-allowed" : "bg-emerald-600 hover:bg-emerald-500")}
                            onClick={handleAiRevision}
                            disabled={aiLoading}
                        >
                            {aiLoading ? (
                                <div className="animate-spin h-4 w-4 border-2 border-white/20 border-t-white rounded-full" />
                            ) : (
                                <Send className="h-4 w-4 text-white" />
                            )}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
