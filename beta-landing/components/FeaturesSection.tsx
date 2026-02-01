"use client";

import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import {
    GraduationCap,
    CheckCircle,
    FileText,
    Search,
    Calculator,
    GitBranch,
    Shield,
    LucideIcon,
} from 'lucide-react';
import { features } from '@/data/constants';

if (typeof window !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
}

const iconMap: Record<string, LucideIcon> = {
    'umat-compliant': GraduationCap,
    'british-english': CheckCircle,
    'references': FileText,
    'real-citations': Search,
    'equations': Calculator,
    'diagrams': GitBranch,
};

export function FeaturesSection() {
    const sectionRef = useRef<HTMLElement>(null);
    const headingRef = useRef<HTMLDivElement>(null);
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

            // Cards stagger animation
            const cards = cardsRef.current?.querySelectorAll('.feature-card');
            if (cards) {
                gsap.fromTo(
                    cards,
                    { opacity: 0, y: 30, scale: 0.95 },
                    {
                        opacity: 1,
                        y: 0,
                        scale: 1,
                        duration: 0.5,
                        stagger: 0.1,
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
            className="py-16 sm:py-24 px-4 sm:px-6 lg:px-8"
        >
            <div className="container max-w-6xl mx-auto">
                <div ref={headingRef} className="text-center mb-12 sm:mb-16" style={{ opacity: 0 }}>
                    {/* Verified Badge */}
                    <div className="mb-6">
                        <span className="verified-badge">
                            <Shield className="w-4 h-4" />
                            Built for Ghanaian Academics
                        </span>
                    </div>

                    <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4">
                        Built for <span className="text-emerald-400">Ghanaian Students</span>
                    </h2>
                    <p className="text-neutral-400 max-w-xl mx-auto">
                        We understand the specific needs of students at UMaT and other Ghanaian universities.
                        Proper referencing, British English, and full university compliance.
                    </p>
                </div>

                <div
                    ref={cardsRef}
                    className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-6"
                >
                    {features.map((feature) => {
                        const Icon = iconMap[feature.id] || GraduationCap;
                        const isHighlight = 'highlight' in feature && feature.highlight;
                        return (
                            <div
                                key={feature.id}
                                className={`feature-card glass-card hover-lift hover-glow tap-feedback p-5 sm:p-6 ${isHighlight ? 'border-emerald-500/30 bg-emerald-500/5' : ''
                                    }`}
                                style={{ opacity: 0 }}
                            >
                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${isHighlight ? 'bg-emerald-500/20' : 'bg-neutral-800/50'
                                    }`}>
                                    <Icon className={`w-6 h-6 ${isHighlight ? 'text-emerald-400' : 'text-neutral-400'}`} />
                                </div>
                                <h3 className="text-lg font-semibold text-white mb-2">
                                    {feature.title}
                                </h3>
                                <p className="text-neutral-400 text-sm leading-relaxed">
                                    {feature.description}
                                </p>
                                {isHighlight && (
                                    <div className="mt-4 pt-3 border-t border-emerald-500/20">
                                        <span className="text-xs text-emerald-400">Primary feature for Ghanaian universities</span>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>
            </div>
        </section>
    );
}
