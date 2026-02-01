"use client";

import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ArrowRight, Sparkles, FileText, CheckCircle, Users } from 'lucide-react';

if (typeof window !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
}

interface HeroProps {
    onCtaClick: (email?: string) => void;
}

export function Hero({ onCtaClick }: HeroProps) {
    const heroRef = useRef<HTMLElement>(null);
    const badgeRef = useRef<HTMLDivElement>(null);
    const headingRef = useRef<HTMLHeadingElement>(null);
    const subheadingRef = useRef<HTMLParagraphElement>(null);
    const ctaRef = useRef<HTMLDivElement>(null);
    const mockupRef = useRef<HTMLDivElement>(null);
    const statsRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            // Create timeline for staggered animations
            const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

            tl.fromTo(
                headingRef.current,
                { opacity: 0, y: 30 },
                { opacity: 1, y: 0, duration: 0.8 }
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
                {/* Badge Removed by user request */}

                {/* Main Heading */}
                <h1
                    ref={headingRef}
                    className="text-3xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold leading-[1.1] mb-6"
                    style={{ opacity: 0 }}
                >
                    <span className="block text-white">It&apos;s 11 PM.</span>
                    <span className="block text-white">Your Presentation is Tomorrow.</span>
                    <span className="block text-emerald-400 mt-2">Built for Ghanaian Academics.</span>
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

                {/* CTA Button with Input */}
                <div
                    ref={ctaRef}
                    className="flex flex-col items-center justify-center w-full max-w-md mx-auto"
                    style={{ opacity: 0 }}
                >
                    <div className="flex flex-col sm:flex-row items-center justify-center gap-3 w-full mb-3">
                        <input
                            type="email"
                            placeholder="Enter your student email..."
                            className="w-full sm:w-auto flex-grow px-6 py-4 rounded-full bg-white/5 border border-white/10 text-white placeholder:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 transition-all text-base"
                            id="hero-email-input"
                        />
                        <button
                            onClick={() => {
                                const emailInput = document.getElementById('hero-email-input') as HTMLInputElement;
                                onCtaClick(emailInput?.value);
                            }}
                            className="w-full sm:w-auto btn btn-primary btn-lg group tap-feedback whitespace-nowrap"
                        >
                            Get Free Access
                            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                        </button>
                    </div>
                    <p className="text-xs text-neutral-500 max-w-xs text-center">
                        <span className="text-emerald-400 font-medium">Beta Program:</span> Help us test SankoSlides and get unrestricted access for free.
                    </p>
                </div>

                {/* Product Mockup - Before/After Preview */}
                <div
                    ref={mockupRef}
                    className="mt-16 sm:mt-24 relative max-w-5xl mx-auto"
                    style={{ opacity: 0 }}
                >
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6 md:gap-16 relative items-center">
                        {/* Before Card (Messy Notes) */}
                        <div className="glass-card p-6 sm:p-8 text-left hover-lift tap-feedback h-auto transform md:rotate-[-2deg] opacity-90">
                            <div className="flex items-center gap-3 mb-4">
                                <div className="w-10 h-10 rounded-xl bg-neutral-800 flex items-center justify-center flex-shrink-0 border border-neutral-700">
                                    <FileText className="w-5 h-5 text-neutral-400" />
                                </div>
                                <span className="text-base font-semibold text-neutral-300">Messy PDF Notes</span>
                            </div>
                            <div className="space-y-3 font-mono text-sm leading-relaxed text-neutral-400 opacity-70">
                                <p className="bg-red-500/10 p-2 rounded text-red-300 inline-block line-through decoration-red-400/50">color: blue</p>
                                <p>galamsey effects on water bodies...</p>
                                <p className="bg-red-500/10 p-2 rounded text-red-300 inline-block">50kg (wrong unit)</p>
                                <p>source: trust me bro (no citation)</p>
                                <div className="h-2 w-3/4 bg-neutral-800 rounded-full animate-pulse mt-2" />
                            </div>
                        </div>

                        {/* Mobile Arrow */}
                        <div className="flex md:hidden justify-center items-center py-2 relative z-10">
                            <div className="w-10 h-10 rounded-full bg-neutral-800 flex items-center justify-center animate-pulse">
                                <ArrowRight className="w-5 h-5 text-neutral-500 rotate-90" />
                            </div>
                        </div>

                        {/* After Card (Real Slide) */}
                        <div className="bg-neutral-900 border border-emerald-500/30 rounded-xl overflow-hidden shadow-2xl shadow-emerald-900/20 transform md:rotate-[1deg] hover:scale-[1.02] transition-transform duration-500">
                            {/* Slide Header */}
                            <div className="bg-emerald-900/20 border-b border-emerald-500/10 p-4 flex justify-between items-center">
                                <span className="text-xs font-bold text-emerald-400 tracking-wider uppercase">SankoSlide #1</span>
                                <div className="flex gap-1">
                                    <div className="w-2 h-2 rounded-full bg-red-400/20"></div>
                                    <div className="w-2 h-2 rounded-full bg-yellow-400/20"></div>
                                    <div className="w-2 h-2 rounded-full bg-green-400/20"></div>
                                </div>
                            </div>

                            {/* Slide Body */}
                            <div className="p-6 sm:p-8 bg-gradient-to-br from-[#0a0a0f] to-[#12121a]">
                                <h3 className="text-xl sm:text-2xl font-bold text-white mb-4">The Impact of Galamsey</h3>
                                <ul className="space-y-4">
                                    <li className="flex items-start gap-3">
                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-2 flex-shrink-0"></div>
                                        <span className="text-neutral-300 text-sm sm:text-base">
                                            Water turbidity levels exceeding <span className="text-emerald-400 font-mono bg-emerald-900/30 px-1 rounded">50 kg/m³</span> in major rivers.
                                        </span>
                                    </li>
                                    <li className="flex items-start gap-3">
                                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 mt-2 flex-shrink-0"></div>
                                        <span className="text-neutral-300 text-sm sm:text-base">
                                            Increased heavy metal <span className="text-emerald-300 font-semibold bg-emerald-500/10 px-1 rounded">colouration</span> visible in satellite imagery.
                                        </span>
                                    </li>
                                </ul>

                                {/* Slide Footer (Citations) */}
                                <div className="mt-8 pt-4 border-t border-white/5 flex justify-between items-end">
                                    <div className="text-[10px] text-neutral-500 font-mono">
                                        Source: Amankwah, R. K. (2024). <span className="italic">Journal of Mining...</span>
                                    </div>
                                    <div className="font-mono text-emerald-500/50 text-[10px]">
                                        f(x) = ∫ turbidity dx
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Connecting Arrow - Desktop only */}
                    <div className="hidden md:flex absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-20 pointer-events-none">
                        <div className="w-12 h-12 rounded-full bg-neutral-900 border border-neutral-700 flex items-center justify-center shadow-xl">
                            <ArrowRight className="w-5 h-5 text-emerald-400" />
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
                    <span className="text-sm">Built for Ghanaian Academics</span>
                </div>
            </div>
        </section>
    );
}
