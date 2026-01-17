"use client";

import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { X, Check, Clock, BookOpen, Ruler, Palette, Coffee, LucideIcon } from 'lucide-react';
import { problems } from '@/data/constants';

if (typeof window !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
}

const iconMap: Record<number, LucideIcon> = {
    0: Palette,
    1: BookOpen,
    2: Ruler,
    3: Clock,
};

export function ProblemSection() {
    const sectionRef = useRef<HTMLElement>(null);
    const headingRef = useRef<HTMLHeadingElement>(null);
    const cardsRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            // Heading animation
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

            // Staggered cards animation
            const cards = cardsRef.current?.querySelectorAll('.problem-card');
            if (cards) {
                gsap.fromTo(
                    cards,
                    { opacity: 0, y: 30 },
                    {
                        opacity: 1,
                        y: 0,
                        duration: 0.5,
                        stagger: 0.15,
                        scrollTrigger: {
                            trigger: cardsRef.current,
                            start: 'top 75%',
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
                <div
                    ref={headingRef}
                    className="text-center mb-10 sm:mb-14"
                    style={{ opacity: 0 }}
                >
                    <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-3">
                        Sound <span className="text-emerald-400">Familiar?</span>
                    </h2>
                    <p className="text-neutral-500 text-sm sm:text-base max-w-lg mx-auto">
                        Every Ghanaian student knows these struggles. We built SankoSlides to fix them.
                    </p>
                </div>

                <div ref={cardsRef} className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
                    {problems.map((problem, index) => {
                        const BeforeIcon = iconMap[index] || Palette;
                        return (
                            <div
                                key={index}
                                className="problem-card glass-card overflow-hidden hover-lift tap-feedback"
                                style={{ opacity: 0 }}
                            >
                                <div className="grid grid-cols-2">
                                    {/* Before side */}
                                    <div className="p-5 sm:p-6 bg-red-500/5 border-r border-neutral-800/50">
                                        <div className="flex items-center gap-2 mb-3">
                                            <X className="w-4 h-4 text-red-400" />
                                            <span className="text-xs font-medium text-red-400 uppercase tracking-wide">Before</span>
                                        </div>
                                        <div className="flex items-start gap-2">
                                            <BeforeIcon className="w-4 h-4 text-neutral-500 mt-0.5 flex-shrink-0" />
                                            <div>
                                                <p className="text-sm text-neutral-300 font-medium">{problem.before.text}</p>
                                                <p className="text-xs text-neutral-500 mt-1">{problem.before.subtext}</p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* After side */}
                                    <div className="p-5 sm:p-6 bg-emerald-500/5">
                                        <div className="flex items-center gap-2 mb-3">
                                            <Check className="w-4 h-4 text-emerald-400" />
                                            <span className="text-xs font-medium text-emerald-400 uppercase tracking-wide">After</span>
                                        </div>
                                        <div>
                                            <p className="text-sm text-emerald-300 font-medium">{problem.after.text}</p>
                                            <p className="text-xs text-neutral-400 mt-1">{problem.after.subtext}</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                </div>

                <p className="text-center text-neutral-500 mt-10 text-sm flex items-center justify-center gap-2">
                    <Coffee className="w-4 h-4" />
                    We&apos;ve been there. That&apos;s why we built SankoSlides.
                </p>
            </div>
        </section>
    );
}
