"use client";

import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ArrowRight, Sparkles, FileText, CheckCircle, Users } from 'lucide-react';

if (typeof window !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
}

interface HeroProps {
    onCtaClick: () => void;
}

export function Hero({ onCtaClick }: HeroProps) {
    const heroRef = useRef<HTMLElement>(null);
    const badgeRef = useRef<HTMLDivElement>(null);
    const headingRef = useRef<HTMLHeadingElement>(null);
    const subheadingRef = useRef<HTMLParagraphElement>(null);
    const ctaRef = useRef<HTMLButtonElement>(null);
    const mockupRef = useRef<HTMLDivElement>(null);
    const statsRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            // Create timeline for staggered animations
            const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

            tl.fromTo(
                badgeRef.current,
                { opacity: 0, y: -20 },
                { opacity: 1, y: 0, duration: 0.6 }
            )
                .fromTo(
                    headingRef.current,
                    { opacity: 0, y: 30 },
                    { opacity: 1, y: 0, duration: 0.8 },
                    '-=0.3'
                )
                .fromTo(
                    subheadingRef.current,
                    { opacity: 0, y: 20 },
                    { opacity: 1, y: 0, duration: 0.6 },
                    '-=0.4'
                )
                .fromTo(
                    ctaRef.current,
                    { opacity: 0, scale: 0.9 },
                    { opacity: 1, scale: 1, duration: 0.5 },
                    '-=0.2'
                )
                .fromTo(
                    mockupRef.current,
                    { opacity: 0, y: 40 },
                    { opacity: 1, y: 0, duration: 0.8 },
                    '-=0.3'
                )
                .fromTo(
                    statsRef.current,
                    { opacity: 0, y: 20 },
                    { opacity: 1, y: 0, duration: 0.5 },
                    '-=0.4'
                );
        }, heroRef);

        return () => ctx.revert();
    }, []);

    return (
        <section
            ref={heroRef}
            className="min-h-screen flex flex-col justify-center px-4 pt-24 pb-12 sm:px-6 lg:px-8 relative overflow-hidden"
        >
            {/* Background orbs */}
            <div className="absolute top-[-20%] left-[10%] w-[500px] h-[500px] bg-orb bg-orb-emerald pointer-events-none" />
            <div className="absolute bottom-[-10%] right-[5%] w-[400px] h-[400px] bg-orb bg-orb-teal pointer-events-none" />

            <div className="container text-center max-w-5xl mx-auto relative z-10">
                {/* Badge */}
                <div
                    ref={badgeRef}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-emerald-500/10 border border-emerald-500/20 mb-6 sm:mb-8"
                    style={{ opacity: 0 }}
                >
                    <Sparkles className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-medium text-emerald-400">
                        Now accepting beta testers
                    </span>
                </div>

                {/* Main Heading */}
                <h1
                    ref={headingRef}
                    className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold leading-[1.1] mb-6"
                    style={{ opacity: 0 }}
                >
                    <span className="block text-white">It&apos;s 11 PM.</span>
                    <span className="block text-white">Your Presentation is Tomorrow.</span>
                    <span className="block text-emerald-400 mt-2">We&apos;ve Got You.</span>
                </h1>

                {/* Subheading */}
                <p
                    ref={subheadingRef}
                    className="text-lg sm:text-xl text-neutral-400 max-w-lg mx-auto mb-8 sm:mb-10 px-4 text-center"
                    style={{ opacity: 0 }}
                >
                    SankoSlides turns your notes, PDFs, and raw ideas into professional,
                    university-grade presentations — in minutes, not hours.
                </p>

                {/* CTA Button */}
                <button
                    ref={ctaRef}
                    onClick={onCtaClick}
                    className="btn btn-primary btn-lg group tap-feedback w-auto max-w-xs sm:max-w-none"
                    style={{ opacity: 0 }}
                >
                    Join the Beta — It&apos;s Free
                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                </button>

                {/* Product Mockup - Before/After Preview */}
                <div
                    ref={mockupRef}
                    className="mt-16 sm:mt-24 relative max-w-5xl mx-auto"
                    style={{ opacity: 0 }}
                >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-16 relative items-stretch">
                        {/* Before Card */}
                        <div className="glass-card p-6 sm:p-8 text-left hover-lift tap-feedback h-full flex flex-col">
                            <div className="flex items-center gap-3 mb-6">
                                <div className="w-10 h-10 rounded-xl bg-red-500/10 flex items-center justify-center flex-shrink-0 border border-red-500/20">
                                    <FileText className="w-5 h-5 text-red-400" />
                                </div>
                                <span className="text-base font-semibold text-neutral-300">Your Notes</span>
                            </div>
                            <div className="space-y-4 flex-grow">
                                <div className="flex items-center gap-4 bg-white/5 p-4 rounded-xl border border-white/5 shadow-sm">
                                    <span className="text-rose-400/80 line-through text-sm font-medium decoration-rose-400/50">Color</span>
                                    <span className="text-neutral-400 text-xs text-right ml-auto font-medium">(US spelling)</span>
                                </div>
                                <div className="flex items-center gap-4 bg-white/5 p-4 rounded-xl border border-white/5 shadow-sm">
                                    <span className="text-neutral-400 text-sm font-medium">Missing citations...</span>
                                </div>
                                <div className="flex items-center gap-4 bg-white/5 p-4 rounded-xl border border-white/5 shadow-sm">
                                    <span className="text-neutral-400 text-sm font-medium">&quot;50kg&quot; → wrong format</span>
                                </div>
                                <div className="h-2 w-3/4 bg-neutral-800 rounded-full animate-pulse mt-2" />
                                <div className="h-2 w-1/2 bg-neutral-800 rounded-full animate-pulse" />
                            </div>
                        </div>

                        {/* Mobile Arrow */}
                        <div className="flex md:hidden justify-center items-center py-4 relative z-10">
                            <div className="w-12 h-12 rounded-full bg-emerald-500 flex items-center justify-center shadow-lg shadow-emerald-500/30 animate-pulse">
                                <ArrowRight className="w-5 h-5 text-white rotate-90" />
                            </div>
                        </div>

                        {/* After Card */}
                        <div className="glass-card-elevated p-6 sm:p-8 text-left hover-lift tap-feedback animate-glow-pulse relative overflow-hidden h-full flex flex-col">
                            <div className="shimmer absolute inset-0 pointer-events-none" />
                            <div className="relative flex-grow flex flex-col h-full z-10">
                                <div className="flex items-center gap-3 mb-6">
                                    <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center flex-shrink-0 border border-emerald-500/30">
                                        <CheckCircle className="w-5 h-5 text-emerald-400" />
                                    </div>
                                    <span className="text-base font-semibold text-emerald-400">SankoSlides Output</span>
                                </div>
                                <div className="space-y-4 flex-grow">
                                    <div className="flex items-center gap-4 bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/10 shadow-sm">
                                        <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                                        <span className="text-emerald-100 text-sm font-medium">Colour</span>
                                        <span className="text-emerald-500/70 text-xs ml-auto">(British English ✓)</span>
                                    </div>
                                    <div className="flex items-center gap-4 bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/10 shadow-sm">
                                        <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                                        <span className="text-emerald-100 text-sm">APA Citations included</span>
                                    </div>
                                    <div className="flex items-center gap-4 bg-emerald-500/5 p-4 rounded-xl border border-emerald-500/10 shadow-sm">
                                        <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                                        <span className="text-emerald-100 text-sm">&quot;50 kg&quot; → SI compliant</span>
                                    </div>
                                </div>
                                {/* Compliance Badge - positioned below content */}
                                <div className="mt-4 pt-4 border-t border-emerald-500/10">
                                    <span className="verified-badge text-xs shadow-lg">
                                        <Sparkles className="w-3 h-3 text-emerald-400" />
                                        University Compliant
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Connecting Arrow - Desktop only */}
                    <div className="hidden md:flex absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20">
                        <div className="w-14 h-14 rounded-full bg-gradient-to-r from-emerald-500 to-teal-500 flex items-center justify-center shadow-xl shadow-emerald-500/40 animate-float border-4 border-[#0a0a0f]">
                            <ArrowRight className="w-6 h-6 text-white" />
                        </div>
                    </div>
                </div>

                {/* Stats/Social Proof */}
                <div
                    ref={statsRef}
                    className="mt-16 sm:mt-24 flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-8 text-neutral-400"
                    style={{ opacity: 0 }}
                >
                    <div className="flex items-center gap-2">
                        <Users className="w-4 h-4 text-emerald-400" />
                        <span className="text-sm">Students across Ghana have already joined</span>
                    </div>
                    <div className="hidden sm:block w-1 h-1 rounded-full bg-neutral-700" />
                    <span className="text-sm">Built for Ghanaian universities</span>
                </div>
            </div>
        </section>
    );
}
