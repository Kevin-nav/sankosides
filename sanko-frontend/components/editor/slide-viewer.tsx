"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { ChevronLeft, ChevronRight, Download, Maximize2, Minimize2, Keyboard } from "lucide-react";
import { useGeneratedSlides } from "@/hooks/api/use-generation";

interface Slide {
    order: number;
    title: string;
    theme_id: string;
    rendered_html: string;
    speaker_notes?: string;
    html_content?: string; // Legacy
}

interface SlideViewerProps {
    sessionId: string;
    onExport?: () => void;
}

export function SlideViewer({ sessionId, onExport }: SlideViewerProps) {
    const { data, isLoading, error } = useGeneratedSlides(sessionId);
    const [currentSlide, setCurrentSlide] = useState(0);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const slides = useMemo<Slide[]>(() => {
        if (!data) return [];
        return (data.presentation?.slides || data.slides || []) as Slide[];
    }, [data]);
    const averageScore = useMemo(() => {
        if (!data) return 0;
        return data.qa_report?.average_score || data.average_visual_score || 0;
    }, [data]);

    // Handle Fullscreen Cleanup / Events
    useEffect(() => {
        const handleFullscreenChange = () => {
            setIsFullscreen(!!document.fullscreenElement);
        };
        document.addEventListener("fullscreenchange", handleFullscreenChange);
        return () => document.removeEventListener("fullscreenchange", handleFullscreenChange);
    }, []);

    const toggleFullscreen = useCallback(async () => {
        if (!containerRef.current) return;
        try {
            if (!document.fullscreenElement) {
                await containerRef.current.requestFullscreen();
            } else {
                await document.exitFullscreen();
            }
        } catch (err) {
            console.error("Fullscreen error:", err);
        }
    }, []);

    // Navigation Logic
    const nextSlide = useCallback(() => {
        if (currentSlide < slides.length - 1) setCurrentSlide(prev => prev + 1);
    }, [currentSlide, slides.length]);

    const prevSlide = useCallback(() => {
        if (currentSlide > 0) setCurrentSlide(prev => prev - 1);
    }, [currentSlide]);

    // Keyboard Navigation (Works in Fullscreen because event bubbles to window/document)
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

            if (e.key === "ArrowRight" || e.key === " ") {
                e.preventDefault();
                // Check current state via functional update logic or ref if needed, 
                // but dependency array handles it here.
                if (currentSlide < slides.length - 1) setCurrentSlide(prev => prev + 1);
            } else if (e.key === "ArrowLeft") {
                e.preventDefault();
                if (currentSlide > 0) setCurrentSlide(prev => prev - 1);
            } else if (e.key === "f" || e.key === "F") {
                e.preventDefault();
                toggleFullscreen();
            } else if (e.key === "Home") {
                e.preventDefault();
                setCurrentSlide(0);
            } else if (e.key === "End") {
                e.preventDefault();
                setCurrentSlide(slides.length - 1);
            }
        };

        window.addEventListener("keydown", handleKeyDown);
        return () => window.removeEventListener("keydown", handleKeyDown);
    }, [slides.length, currentSlide, toggleFullscreen]); // Added currentSlide to deps for correct closuring

    if (isLoading) {
        return (
            <div className="flex h-full w-full flex-col items-center justify-center bg-neutral-950">
                <div className="h-10 w-10 animate-spin rounded-full border-3 border-emerald-500 border-t-transparent"></div>
                <p className="mt-4 text-neutral-400 font-mono text-sm">Loading presentation...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex h-full w-full flex-col items-center justify-center text-center bg-neutral-950 p-6">
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 max-w-md">
                    <p className="text-red-400 font-medium">Failed to load slides</p>
                </div>
            </div>
        );
    }

    if (slides.length === 0) {
        return (
            <div className="flex h-full w-full flex-col items-center justify-center text-center bg-neutral-950">
                <p className="text-neutral-400">No slides found.</p>
            </div>
        );
    }

    return (
        <div
            ref={containerRef}
            className={`flex h-full w-full flex-col bg-neutral-950 overflow-hidden ${isFullscreen ? 'fixed inset-0 z-50' : 'relative'
                }`}
        >
            {/* Header / Controls - Hidden in FS unless hovered */}
            <div
                className={`
                    flex items-center justify-between px-4 py-3 z-20
                    transition-all duration-300
                    ${isFullscreen
                        ? 'absolute top-0 left-0 right-0 bg-gradient-to-b from-black/80 to-transparent opacity-0 hover:opacity-100'
                        : 'border-b border-neutral-800 bg-neutral-900/50'
                    }
                `}
            >
                <div className="flex items-center gap-4">
                    <h2 className={`font-semibold text-white ${isFullscreen ? 'text-sm font-mono' : 'text-lg'}`}>
                        Slide {currentSlide + 1} of {slides.length}
                    </h2>
                    {averageScore > 0 && !isFullscreen && (
                        <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-sm text-emerald-400">
                            Score: {Math.round(averageScore * 100)}%
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-white/50 text-xs flex items-center gap-1 mr-2 hidden sm:flex">
                        <Keyboard className="h-3 w-3" />
                        Nav: Arrows | Full: F
                    </span>
                    <button
                        onClick={toggleFullscreen}
                        className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-neutral-300 hover:bg-neutral-800 transition-colors"
                        title={isFullscreen ? "Exit (Esc)" : "Fullscreen (F)"}
                    >
                        {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
                        {!isFullscreen && <span className="hidden sm:inline">Fullscreen</span>}
                    </button>
                    {onExport && !isFullscreen && (
                        <button
                            onClick={onExport}
                            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700 transition-colors"
                        >
                            <Download className="h-4 w-4" />
                            <span className="hidden sm:inline">Export</span>
                        </button>
                    )}
                </div>
            </div>

            {/* Slide Area */}
            <div className={`flex-1 relative flex items-center justify-center bg-black ${isFullscreen ? '' : 'p-4 md:p-8'}`}>
                {/* 
                    EAGER RENDERING: Map all slides to iframes. 
                    - In Fullscreen: No max-width constraints. We use CSS transform or w/h 100% object-contain logic.
                      Since standard slides are often fixed width, we wrap them in a container that scales.
                    - For simplicity here, we assume standard responsiveness or use the aspect-video container.
                */}
                <div
                    className={`
                        relative transition-all duration-300
                        ${isFullscreen
                            ? 'w-full h-full'
                            : 'w-full max-w-6xl aspect-video rounded-xl border border-neutral-700 shadow-2xl overflow-hidden bg-white'
                        }
                    `}
                >
                    {slides.map((slide, idx) => (
                        <div
                            key={idx}
                            style={{ display: idx === currentSlide ? 'flex' : 'none' }}
                            className={`
                                w-full h-full items-center justify-center
                                ${isFullscreen ? '' : ''}
                            `}
                        >
                            {/* 
                                In separate-container mode (non-fullscreen), the parent enforces aspect-video.
                                In fullscreen, we need to enforce centering and aspect ratio manually if the slide content doesn't fill.
                                Assuming generated HTML handles full width, or we center a 16:9 box.
                            */}
                            {isFullscreen ? (
                                <div className="w-full h-full flex items-center justify-center p-0">
                                    {/* This wrapper forces a 16:9 max ratio fit within the screen */}
                                    <div className="aspect-video w-full h-full max-h-screen max-w-[177.78vh] bg-white shadow-2xl">
                                        <iframe
                                            srcDoc={slide.rendered_html || slide.html_content || ""}
                                            className="w-full h-full border-0"
                                            title={`Slide ${idx + 1}`}
                                            sandbox="allow-same-origin allow-scripts"
                                        />
                                    </div>
                                </div>
                            ) : (
                                <iframe
                                    srcDoc={slide.rendered_html || slide.html_content || ""}
                                    className="w-full h-full border-0"
                                    title={`Slide ${idx + 1}`}
                                    sandbox="allow-same-origin allow-scripts"
                                />
                            )}
                        </div>
                    ))}
                </div>

                {/* Navigation Arrows (Overlay) */}
                <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 flex justify-between px-4 pointer-events-none">
                    <button
                        onClick={prevSlide}
                        disabled={currentSlide === 0}
                        className="pointer-events-auto p-3 rounded-full bg-black/50 hover:bg-black/70 text-white/70 hover:text-white disabled:opacity-0 transition-opacity"
                    >
                        <ChevronLeft className="h-8 w-8" />
                    </button>
                    <button
                        onClick={nextSlide}
                        disabled={currentSlide === slides.length - 1}
                        className="pointer-events-auto p-3 rounded-full bg-black/50 hover:bg-black/70 text-white/70 hover:text-white disabled:opacity-0 transition-opacity"
                    >
                        <ChevronRight className="h-8 w-8" />
                    </button>
                </div>
            </div>

            {/* Bottom Bar - Hidden in FS unless hovered */}
            <div
                className={`
                    px-4 py-3 z-20 flex justify-center
                    transition-all duration-300
                    ${isFullscreen
                        ? 'absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent opacity-0 hover:opacity-100'
                        : 'border-t border-neutral-800 bg-neutral-900/50'
                    }
                `}
            >
                <div className="flex gap-2">
                    {slides.map((_, idx) => (
                        <button
                            key={idx}
                            onClick={() => setCurrentSlide(idx)}
                            className={`
                                h-1.5 rounded-full transition-all duration-300
                                ${idx === currentSlide
                                    ? 'w-6 bg-emerald-500'
                                    : 'w-1.5 bg-neutral-700 hover:bg-neutral-500'
                                }
                            `}
                        />
                    ))}
                </div>
            </div>
        </div>
    );
}
