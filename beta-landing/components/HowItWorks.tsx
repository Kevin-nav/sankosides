"use client";

import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ArrowRight, FileUp, MessageSquare, Download, Sparkles } from 'lucide-react';

if (typeof window !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
}

const steps = [
    {
        number: "01",
        icon: FileUp,
        title: "Drop your notes or PDF",
        description: "Upload your lecture notes, research papers, or just type your topic. We handle PDFs, Word docs, and plain text.",
        visual: (
            <div className="relative">
                <div className="w-16 h-20 bg-red-500/10 rounded-lg border border-red-500/20 flex items-center justify-center">
                    <span className="text-xs text-red-400 font-mono">.PDF</span>
                </div>
                <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-emerald-500 rounded-full flex items-center justify-center">
                    <ArrowRight className="w-3 h-3 text-white rotate-90" />
                </div>
            </div>
        ),
    },
    {
        number: "02",
        icon: MessageSquare,
        title: "Tell us what you need",
        description: "How many slides? What's the focus? Our AI asks quick questions to understand your assignment perfectly.",
        visual: (
            <div className="space-y-2">
                <div className="flex gap-2">
                    <div className="w-8 h-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-emerald-400" />
                    </div>
                    <div className="bg-neutral-800/50 rounded-lg rounded-tl-none px-3 py-2 text-xs text-neutral-300 max-w-[140px]">
                        How many slides?
                    </div>
                </div>
                <div className="flex gap-2 justify-end">
                    <div className="bg-emerald-500/20 rounded-lg rounded-tr-none px-3 py-2 text-xs text-emerald-300">
                        About 15 slides
                    </div>
                </div>
            </div>
        ),
    },
    {
        number: "03",
        icon: Download,
        title: "Get professional slides",
        description: "Download presentation-ready slides with proper citations and formatting. Formats specifically for UMaT department standards.",
        visual: (
            <div className="relative">
                <div className="w-full bg-emerald-500/10 rounded-lg border border-emerald-500/20 p-3">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-orange-500/20 rounded flex items-center justify-center">
                                <span className="text-[10px] text-orange-400 font-mono">.PPTX</span>
                            </div>
                            <div>
                                <p className="text-xs text-white font-medium">Presentation.pptx</p>
                                <p className="text-[10px] text-neutral-500">15 slides • UMaT format</p>
                            </div>
                        </div>
                        <Download className="w-4 h-4 text-emerald-400" />
                    </div>
                </div>
            </div>
        ),
    },
];

interface HowItWorksProps {
    onCtaClick: () => void;
}

export function HowItWorks({ onCtaClick }: HowItWorksProps) {
    const sectionRef = useRef<HTMLElement>(null);
    const headingRef = useRef<HTMLHeadingElement>(null);
    const stepsRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            gsap.fromTo(
                headingRef.current,
                { opacity: 0, y: 30 },
                {
                    opacity: 1,
                    y: 0,
                    duration: 0.6,
                    scrollTrigger: {
                        trigger: headingRef.current,
                        start: 'top 80%',
                        toggleActions: 'play none none reverse',
                    },
                }
            );

            const stepItems = stepsRef.current?.querySelectorAll('.step-item');
            if (stepItems) {
                gsap.fromTo(
                    stepItems,
                    { opacity: 0, y: 40 },
                    {
                        opacity: 1,
                        y: 0,
                        duration: 0.6,
                        stagger: 0.2,
                        scrollTrigger: {
                            trigger: stepsRef.current,
                            start: 'top 70%',
                            toggleActions: 'play none none reverse',
                        },
                    }
                );
            }
        }, sectionRef);

        return () => ctx.revert();
    }, []);

    return (
        <section
            ref={sectionRef}
            className="py-16 sm:py-24 px-4 sm:px-6 lg:px-8 bg-[#08080e]"
        >
            <div className="container max-w-5xl mx-auto">
                <h2
                    ref={headingRef}
                    className="text-2xl sm:text-3xl md:text-4xl font-bold text-center mb-12 sm:mb-16"
                    style={{ opacity: 0 }}
                >
                    How It <span className="text-emerald-400">Works</span>
                </h2>

                <div ref={stepsRef} className="space-y-6 sm:space-y-0 sm:grid sm:grid-cols-3 sm:gap-6 mb-12">
                    {steps.map((step, index) => {
                        const Icon = step.icon;
                        return (
                            <div
                                key={index}
                                className="step-item glass-card p-5 sm:p-6 hover-lift tap-feedback relative overflow-hidden"
                                style={{ opacity: 0 }}
                            >
                                {/* Step number watermark */}
                                <span className="absolute top-4 right-4 text-6xl font-bold text-neutral-800/30">
                                    {step.number}
                                </span>

                                <div className="relative">
                                    {/* Icon */}
                                    <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4">
                                        <Icon className="w-5 h-5 text-emerald-400" />
                                    </div>

                                    {/* Content */}
                                    <h3 className="text-lg font-semibold text-white mb-2">
                                        {step.title}
                                    </h3>
                                    <p className="text-neutral-400 text-sm mb-4">
                                        {step.description}
                                    </p>

                                    {/* Visual representation */}
                                    <div className="mt-4 pt-4 border-t border-neutral-800/50">
                                        {step.visual}
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <div className="text-center">
                    <button onClick={onCtaClick} className="btn btn-primary group tap-feedback">
                        Get Started
                        <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </button>
                    <p className="text-neutral-500 text-xs mt-4">
                        Formats specifically for UMaT department standards
                    </p>
                </div>
            </div>
        </section>
    );
}
