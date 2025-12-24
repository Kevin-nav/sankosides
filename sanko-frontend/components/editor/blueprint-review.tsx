"use client";

import { useState, useEffect } from "react";
import { DragDropContext, Droppable, Draggable, DropResult } from "@hello-pangea/dnd";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Check, GripVertical, Plus, Trash2, Edit2, Send, Wand2 } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface SlideSkeleton {
    order: number;
    title: string;
    content_type: string;
    // content_description replaces bullet_points for the review phase as per user request
    content_description?: string;
    bullet_points: string[]; // Keep for compatibility, but UI focuses on description
    needs_citation: boolean;
    needs_diagram: boolean;
}

interface BlueprintReviewProps {
    sessionId: string;
    onApprove: (modified: boolean) => void;
}

export function BlueprintReview({ sessionId, onApprove }: BlueprintReviewProps) {
    const { user } = useAuth();
    const [skeleton, setSkeleton] = useState<{ title: string, slides: SlideSkeleton[] } | null>(null);
    const [loading, setLoading] = useState(true);
    const [aiInput, setAiInput] = useState("");
    const [aiLoading, setAiLoading] = useState(false);

    useEffect(() => {
        if (!sessionId || !user) return;
        loadBlueprint();
    }, [sessionId, user]);

    async function loadBlueprint() {
        if (!user) return;
        const token = await user.getIdToken();
        const res = await fetch(`/api/generate/blueprint/${sessionId}`, {
            headers: { "Authorization": `Bearer ${token}` }
        });
        if (res.ok) {
            const data = await res.json();
            // Ensure content_description exists
            const slides = data.slides.map((s: any) => ({
                ...s,
                content_description: s.content_description || s.key_points?.[0] || "No description provided."
            }));
            setSkeleton({ title: data.title, slides });
        }
        setLoading(false);
    }

    const onDragEnd = (result: DropResult) => {
        if (!result.destination || !skeleton) return;
        const items = Array.from(skeleton.slides);
        const [reorderedItem] = items.splice(result.source.index, 1);
        items.splice(result.destination.index, 0, reorderedItem);
        // Update order property
        const updated = items.map((slide, index) => ({ ...slide, order: index + 1 }));
        setSkeleton({ ...skeleton, slides: updated });
    };

    const handleAiRevision = async () => {
        if (!aiInput.trim() || !user) return;
        setAiLoading(true);
        try {
            const token = await user.getIdToken();
            const res = await fetch("/api/generate/clarify", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ session_id: sessionId, answer: aiInput }) // User request for revision
            });

            if (res.ok) {
                const data = await res.json();
                if (data.status === "blueprint_ready") {
                    await loadBlueprint(); // Reload updated blueprint
                    setAiInput("");
                }
            }
        } catch (e) {
            console.error(e);
        } finally {
            setAiLoading(false);
        }
    };

    const handleApprove = async () => {
        if (!user || !skeleton) return;
        try {
            const token = await user.getIdToken();
            const res = await fetch("/api/generate/approve", {
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

            if (res.ok) {
                onApprove(true);
            }
        } catch (e) {
            console.error(e);
        }
    };

    if (loading) return <div className="p-8 text-neutral-400">Loading blueprint...</div>;
    if (!skeleton) return <div className="p-8 text-red-400">Failed to load blueprint.</div>;

    return (
        <div className="flex h-full flex-col bg-neutral-950 p-6 text-white max-w-5xl mx-auto w-full">
            <div className="mb-6 flex items-center justify-between sticky top-0 bg-neutral-950/80 backdrop-blur-md z-10 py-4 border-b border-white/5">
                <div>
                    <h2 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-400 to-cyan-400">
                        {skeleton.title || "Review Structure"}
                    </h2>
                    <p className="text-neutral-400 text-sm mt-1">
                        Refine the outline. Drag to reorder, edit titles, or ask AI to make changes.
                    </p>
                </div>
                <div className="flex gap-4">
                    <Button onClick={handleApprove} className="bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/20 shadow-lg">
                        <Check className="mr-2 h-4 w-4" />
                        Approve & Generate
                    </Button>
                </div>
            </div>

            <div className="flex-1 overflow-hidden flex gap-6">
                {/* Visual Outline (Drag & Drop) */}
                <div className="flex-1 overflow-y-auto custom-scrollbar pr-2">
                    <DragDropContext onDragEnd={onDragEnd}>
                        <Droppable droppableId="slides">
                            {(provided) => (
                                <div {...provided.droppableProps} ref={provided.innerRef} className="space-y-4 pb-20">
                                    {skeleton.slides.map((slide, idx) => (
                                        <Draggable key={idx.toString()} draggableId={idx.toString()} index={idx}>
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
                                                        <div {...provided.dragHandleProps} className="mt-1 flex h-6 w-6 cursor-grab items-center justify-center rounded text-neutral-600 hover:text-emerald-400 active:cursor-grabbing">
                                                            <GripVertical className="h-5 w-5" />
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
                                                                }}
                                                                className="min-h-[60px] resize-none border-transparent bg-neutral-950/30 p-2 text-sm text-neutral-300 focus:bg-neutral-950 focus:ring-1 focus:ring-emerald-500/50"
                                                                placeholder="Briefly describe what goes on this slide..."
                                                            />
                                                        </div>

                                                        <Button variant="ghost" size="icon" className="text-neutral-600 hover:text-red-400 hover:bg-red-500/10"
                                                            onClick={() => {
                                                                const newSlides = skeleton.slides.filter((_, i) => i !== idx);
                                                                setSkeleton({ ...skeleton, slides: newSlides });
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
                                        className="w-full border-dashed border-neutral-800 text-neutral-500 hover:text-emerald-400 hover:border-emerald-500/50 hover:bg-emerald-500/5 py-8"
                                        onClick={() => {
                                            const newSlides = [...skeleton.slides, {
                                                order: skeleton.slides.length + 1,
                                                title: "New Slide",
                                                content_type: "body",
                                                content_description: "New slide description.",
                                                bullet_points: [],
                                                needs_citation: false,
                                                needs_diagram: false
                                            }];
                                            setSkeleton({ ...skeleton, slides: newSlides });
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
