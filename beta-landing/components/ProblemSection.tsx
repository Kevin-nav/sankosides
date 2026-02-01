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
                                className="problem-card bg-neutral-900/40 border border-white/5 rounded-2xl overflow-hidden hover:border-white/10 transition-colors"
                                style={{ opacity: 0 }}
                            >
                                <div className="grid grid-cols-2 h-full">
                                    {/* Before side */}
                                    <div className="p-3 sm:p-5 md:p-6 bg-red-950/20 border-r border-white/5 flex flex-col justify-center">
                                        <div className="flex items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3">
                                            <X className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-red-400" />
                                            <span className="text-[9px] sm:text-[10px] font-bold text-red-400 uppercase tracking-widest">Before</span>
                                        </div>
                                        <div className="flex flex-col sm:flex-row items-start gap-2 sm:gap-3">
                                            <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                                                <BeforeIcon className="w-3.5 h-3.5 sm:w-4 sm:h-4 text-red-400" />
                                            </div>
                                            <div className="min-w-0">
                                                <p className="text-xs sm:text-sm text-neutral-200 font-medium leading-tight break-words">{problem.before.text}</p>
                                                <p className="text-[10px] sm:text-xs text-neutral-500 mt-1 sm:mt-1.5 leading-tight">{problem.before.subtext}</p>
                                            </div>
                                        </div>
                                    </div>

                                    {/* After side */}
                                    <div className="p-3 sm:p-5 md:p-6 bg-emerald-950/20 flex flex-col justify-center">
                                        <div className="flex items-center gap-1.5 sm:gap-2 mb-2 sm:mb-3">
                                            <Check className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-emerald-400" />
                                            <span className="text-[9px] sm:text-[10px] font-bold text-emerald-400 uppercase tracking-widest">After</span>
                                        </div>
                                        <div className="flex flex-col sm:block pl-0">
                                            <p className="text-xs sm:text-sm text-emerald-100 font-medium leading-tight break-words">{problem.after.text}</p>
                                            <p className="text-[10px] sm:text-xs text-emerald-500/70 mt-1 sm:mt-1.5 leading-tight">{problem.after.subtext}</p>
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
