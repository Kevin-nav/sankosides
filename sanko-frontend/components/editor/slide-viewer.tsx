"use client";

import { useState, useEffect } from "react";
import { ChevronLeft, ChevronRight, Download, Maximize2, ExternalLink } from "lucide-react";

interface Slide {
    order: number;
    html_content: string;
    visual_score: number;
    visual_issues: string[];
    iterations: number;
}

interface SlideViewerProps {
    sessionId: string;
    onExport?: () => void;
}

export function SlideViewer({ sessionId, onExport }: SlideViewerProps) {
    const [slides, setSlides] = useState<Slide[]>([]);
    const [currentSlide, setCurrentSlide] = useState(0);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [averageScore, setAverageScore] = useState(0);

    useEffect(() => {
        async function fetchSlides() {
            try {
                setLoading(true);
                const res = await fetch(`/api/generate/result/${sessionId}`);

                if (!res.ok) {
                    throw new Error(`Failed to fetch slides: ${res.status}`);
                }

                const data = await res.json();
                setSlides(data.slides || []);
                setAverageScore(data.average_visual_score || 0);
            } catch (err: any) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }

        if (sessionId) {
            fetchSlides();
        }
    }, [sessionId]);

    const nextSlide = () => {
        if (currentSlide < slides.length - 1) {
            setCurrentSlide(currentSlide + 1);
        }
    };

    const prevSlide = () => {
        if (currentSlide > 0) {
            setCurrentSlide(currentSlide - 1);
        }
    };

    if (loading) {
        return (
            <div className="flex h-full w-full flex-col items-center justify-center">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald-500 border-t-transparent"></div>
                <p className="mt-4 text-neutral-400">Loading slides...</p>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex h-full w-full flex-col items-center justify-center text-center">
                <p className="text-red-500">Error: {error}</p>
            </div>
        );
    }

    if (slides.length === 0) {
        return (
            <div className="flex h-full w-full flex-col items-center justify-center text-center">
                <p className="text-neutral-400">No slides found.</p>
            </div>
        );
    }

    const slide = slides[currentSlide];

    return (
        <div className="flex h-full w-full flex-col">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-neutral-800 px-4 py-3">
                <div className="flex items-center gap-4">
                    <h2 className="text-lg font-semibold text-white">
                        Slide {currentSlide + 1} of {slides.length}
                    </h2>
                    <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-sm text-emerald-400">
                        Score: {Math.round(averageScore * 100)}%
                    </span>
                </div>
                <div className="flex items-center gap-2">
                    {onExport && (
                        <button
                            onClick={onExport}
                            className="flex items-center gap-2 rounded-lg bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-700"
                        >
                            <Download className="h-4 w-4" />
                            Export
                        </button>
                    )}
                </div>
            </div>

            {/* Slide Display */}
            <div className="flex-1 overflow-hidden p-4">
                <div className="relative mx-auto h-full max-w-4xl">
                    {/* Slide Frame */}
                    <div className="aspect-video w-full overflow-hidden rounded-lg border border-neutral-800 bg-white shadow-2xl">
                        <iframe
                            srcDoc={slide.html_content}
                            className="h-full w-full"
                            title={`Slide ${currentSlide + 1}`}
                            sandbox="allow-same-origin"
                        />
                    </div>

                    {/* Slide Info */}
                    <div className="mt-3 flex items-center justify-between text-sm text-neutral-400">
                        <span>Visual Score: {Math.round(slide.visual_score * 100)}%</span>
                        {slide.visual_issues.length > 0 && (
                            <span className="text-amber-400">
                                {slide.visual_issues.length} issue(s)
                            </span>
                        )}
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between border-t border-neutral-800 px-4 py-3">
                <button
                    onClick={prevSlide}
                    disabled={currentSlide === 0}
                    className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-neutral-300 hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                </button>

                {/* Slide Dots */}
                <div className="flex items-center gap-2">
                    {slides.map((_, idx) => (
                        <button
                            key={idx}
                            onClick={() => setCurrentSlide(idx)}
                            className={`h-2 w-2 rounded-full transition-colors ${idx === currentSlide
                                ? "bg-emerald-500"
                                : "bg-neutral-700 hover:bg-neutral-600"
                                }`}
                        />
                    ))}
                </div>

                <button
                    onClick={nextSlide}
                    disabled={currentSlide === slides.length - 1}
                    className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-neutral-300 hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50"
                >
                    Next
                    <ChevronRight className="h-4 w-4" />
                </button>
            </div>
        </div>
    );
}
