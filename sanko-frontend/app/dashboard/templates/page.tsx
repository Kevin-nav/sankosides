"use client";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Layers, Play, X, ChevronLeft, ChevronRight, Maximize2 } from "lucide-react";
import { useState, useEffect, useCallback, useRef } from "react";
import { useTemplates, useThemes, getPreviewUrl } from "@/hooks/convex";

// Slide types to cycle through in the preview
const PREVIEW_SLIDE_TYPES = ["title", "content", "two_column", "section", "conclusion"];

export default function TemplatesPage() {
    const { loading: authLoading } = useAuth();
    // Convex hooks - direct queries, no API round-trip
    const templates = useTemplates() ?? [];
    const themes = useThemes() ?? [];
    const loading = templates === undefined || themes === undefined;

    // Fullscreen Preview State
    const [previewOpen, setPreviewOpen] = useState(false);
    const [selectedTheme, setSelectedTheme] = useState<typeof themes[0] | null>(null);
    const [currentSlideIndex, setCurrentSlideIndex] = useState(0);
    const previewContainerRef = useRef<HTMLDivElement>(null);

    // Keyboard navigation
    useEffect(() => {
        if (!previewOpen) return;

        const handleKeyDown = (e: KeyboardEvent) => {
            switch (e.key) {
                case "ArrowRight":
                case " ": // Spacebar
                    e.preventDefault();
                    setCurrentSlideIndex(prev =>
                        prev < PREVIEW_SLIDE_TYPES.length - 1 ? prev + 1 : 0
                    );
                    break;
                case "ArrowLeft":
                    e.preventDefault();
                    setCurrentSlideIndex(prev =>
                        prev > 0 ? prev - 1 : PREVIEW_SLIDE_TYPES.length - 1
                    );
                    break;
                case "f":
                case "F":
                    e.preventDefault();
                    toggleFullscreen();
                    break;
                case "Escape":
                    // If in native fullscreen, let browser handle it.
                    // If just in our overlay, close it.
                    if (!document.fullscreenElement) {
                        setPreviewOpen(false);
                    }
                    break;
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [previewOpen]);

    const openPreview = (theme: typeof themes[0]) => {
        setSelectedTheme(theme);
        setCurrentSlideIndex(0);
        setPreviewOpen(true);
    };

    const toggleFullscreen = async () => {
        if (!previewContainerRef.current) return;
        try {
            if (!document.fullscreenElement) {
                await previewContainerRef.current.requestFullscreen();
            } else {
                await document.exitFullscreen();
            }
        } catch (err) {
            console.error("Fullscreen error:", err);
        }
    };

    const nextSlide = () => {
        setCurrentSlideIndex(prev =>
            prev < PREVIEW_SLIDE_TYPES.length - 1 ? prev + 1 : 0
        );
    };

    const prevSlide = () => {
        setCurrentSlideIndex(prev =>
            prev > 0 ? prev - 1 : PREVIEW_SLIDE_TYPES.length - 1
        );
    };

    const currentSlideType = PREVIEW_SLIDE_TYPES[currentSlideIndex];

    // Fetch preview HTML (still uses backend for Jinja2 rendering)
    const [previewHtml, setPreviewHtml] = useState<string>("");
    const [previewLoading, setPreviewLoading] = useState(false);

    useEffect(() => {
        if (!previewOpen || !selectedTheme) return;
        setPreviewLoading(true);
        const url = getPreviewUrl(selectedTheme.themeId, currentSlideType);
        fetch(url)
            .then(res => res.text())
            .then(html => {
                setPreviewHtml(html);
                setPreviewLoading(false);
            })
            .catch(() => setPreviewLoading(false));
    }, [previewOpen, selectedTheme, currentSlideType]);

    // Prefetch cache for preview HTML
    const previewCache = useRef<Map<string, string>>(new Map());

    // Prefetch on hover
    const prefetchTheme = (themeId: string) => {
        if (previewCache.current.has(themeId)) return;
        const url = getPreviewUrl(themeId, "title");
        fetch(url)
            .then(res => res.text())
            .then(html => previewCache.current.set(themeId, html))
            .catch(() => { });
    };

    if (authLoading || loading) {
        return (
            <div className="flex items-center justify-center p-8 h-[50vh]">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
            </div>
        );
    }

    return (
        <>
            <div className="flex flex-col space-y-6 p-4 md:p-8 pt-6">
                {/* Header */}
                <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                    <div className="space-y-1">
                        <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white">Themes</h2>
                        <p className="text-neutral-400">Choose a visual theme for your presentations. Click to preview all slide types.</p>
                    </div>
                </div>

                {/* Theme Cards Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {themes.map((theme) => (
                        <Card
                            key={theme._id}
                            className="group bg-neutral-900 border-neutral-800 hover:border-neutral-600 transition-all cursor-pointer overflow-hidden"
                            onClick={() => openPreview(theme)}
                            onMouseEnter={() => prefetchTheme(theme.themeId)}
                        >
                            {/* Color Preview Bar */}
                            <div className="h-3 flex">
                                {theme.palette && Object.values(theme.palette.colors).slice(0, 5).map((color, i) => (
                                    <div
                                        key={i}
                                        className="flex-1"
                                        style={{ backgroundColor: color as string }}
                                    />
                                ))}
                            </div>

                            {/* Preview Area */}
                            <div className="h-40 bg-neutral-800 relative overflow-hidden">
                                <div className="absolute inset-0 flex items-center justify-center">
                                    <Layers className="h-16 w-16 text-neutral-700" />
                                </div>

                                {/* Hover Overlay */}
                                <div className="absolute inset-0 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                                    <Button variant="secondary" size="sm" className="bg-white/10 hover:bg-white/20 text-white border-white/20">
                                        <Play className="mr-2 h-4 w-4" />
                                        Preview Slides
                                    </Button>
                                </div>
                            </div>

                            <CardHeader className="pb-2">
                                <CardTitle className="text-lg text-white">{theme.name}</CardTitle>
                                <CardDescription className="text-neutral-400 line-clamp-2">
                                    {theme.description || "A beautiful theme for your presentations"}
                                </CardDescription>
                            </CardHeader>

                            <CardFooter className="flex justify-between items-center pt-2 border-t border-neutral-800">
                                <div className="flex gap-1">
                                    {theme.palette && Object.values(theme.palette.colors).slice(0, 4).map((color, i) => (
                                        <div
                                            key={i}
                                            className="w-5 h-5 rounded-full border border-neutral-700"
                                            style={{ backgroundColor: color as string }}
                                        />
                                    ))}
                                </div>
                                <Badge variant="secondary" className="bg-neutral-800 text-neutral-300 text-xs">
                                    {templates.filter(t => t.category === "general").length} slides
                                </Badge>
                            </CardFooter>
                        </Card>
                    ))}
                </div>
            </div>

            {/* Fullscreen Preview Overlay */}
            {previewOpen && selectedTheme && (
                <div
                    ref={previewContainerRef}
                    className="fixed inset-0 z-50 bg-neutral-950 flex flex-col"
                >
                    {/* Top Bar */}
                    <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-800 bg-neutral-950">
                        <div>
                            <h3 className="text-lg font-semibold text-white">{selectedTheme.name}</h3>
                            <p className="text-sm text-neutral-400">
                                Slide {currentSlideIndex + 1} of {PREVIEW_SLIDE_TYPES.length} •
                                <span className="capitalize ml-1">{currentSlideType.replace("_", " ")}</span>
                            </p>
                        </div>

                        <div className="flex items-center gap-4">
                            <div className="text-sm text-neutral-500 hidden sm:block">
                                Use ← → arrows or spacebar to navigate
                            </div>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={toggleFullscreen}
                                className="text-neutral-400 hover:text-white"
                                title="Toggle Fullscreen (F)"
                            >
                                <Maximize2 className="h-5 w-5" />
                            </Button>
                            <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => setPreviewOpen(false)}
                                className="text-neutral-400 hover:text-white"
                            >
                                <X className="h-5 w-5" />
                            </Button>
                        </div>
                    </div>

                    {/* Slide Preview Area */}
                    <div className="flex-1 flex items-center justify-center p-8 relative bg-neutral-950">
                        {/* Navigation Buttons */}
                        <button
                            onClick={prevSlide}
                            className="absolute left-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-neutral-800/80 hover:bg-neutral-700 text-white transition-colors"
                        >
                            <ChevronLeft className="h-6 w-6" />
                        </button>

                        <button
                            onClick={nextSlide}
                            className="absolute right-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-neutral-800/80 hover:bg-neutral-700 text-white transition-colors"
                        >
                            <ChevronRight className="h-6 w-6" />
                        </button>

                        {/* Slide Container - 16:9 aspect ratio */}
                        <div className="w-full max-w-[1280px] aspect-video shadow-2xl rounded-lg overflow-hidden border border-neutral-700 bg-white relative">
                            {previewLoading || !previewHtml ? (
                                <div className="absolute inset-0 flex items-center justify-center bg-neutral-900">
                                    <Loader2 className="h-10 w-10 animate-spin text-emerald-500" />
                                </div>
                            ) : (
                                <iframe
                                    srcDoc={previewHtml}
                                    className="w-full h-full border-0"
                                    title="Slide Preview"
                                    sandbox="allow-same-origin allow-scripts"
                                />
                            )}
                        </div>
                    </div>

                    {/* Bottom Navigation Dots */}
                    <div className="flex items-center justify-center gap-2 py-4 border-t border-neutral-800 bg-neutral-950">
                        {PREVIEW_SLIDE_TYPES.map((type, index) => (
                            <button
                                key={type}
                                onClick={() => setCurrentSlideIndex(index)}
                                className={`w-3 h-3 rounded-full transition-all ${index === currentSlideIndex
                                    ? "bg-emerald-500 w-6"
                                    : "bg-neutral-600 hover:bg-neutral-500"
                                    }`}
                                title={type.replace("_", " ")}
                            />
                        ))}
                    </div>
                </div>
            )}
        </>
    );
}
