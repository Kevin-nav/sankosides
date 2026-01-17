import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import {
    FileText,
    CheckCircle,
    Calculator,
    GitBranch,
    Search,
    GraduationCap,
    Shield,
} from 'lucide-react';

gsap.registerPlugin(ScrollTrigger);

const features = [
    {
        icon: GraduationCap,
        title: "UMaT Compliant",
        description: "Built with Ghanaian university formatting rules in mind. Your lecturers will approve.",
        highlight: true,
    },
    {
        icon: CheckCircle,
        title: "No More US Spelling Marks",
        description: '"Colour" not "color", "organisation" not "organization". Never lose marks again.',
        highlight: false,
    },
    {
        icon: FileText,
        title: "Proper References",
        description: "APA, Harvard, IEEE — citations formatted exactly how your lecturers want them.",
        highlight: false,
    },
    {
        icon: Search,
        title: "Real Citations",
        description: "We find actual academic papers with DOIs. No fake references, no hallucinations.",
        highlight: false,
    },
    {
        icon: Calculator,
        title: "Perfect Equations",
        description: "Complex LaTeX math rendered beautifully. From thermodynamics to quantum mechanics.",
        highlight: false,
    },
    {
        icon: GitBranch,
        title: "Smart Diagrams",
        description: "Flowcharts, process diagrams, geological maps — describe it, we create it.",
        highlight: false,
    },
];

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
                            Verified for UMaT Standards
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
                    {features.map((feature, index) => {
                        const Icon = feature.icon;
                        return (
                            <div
                                key={index}
                                className={`feature-card glass-card hover-lift hover-glow tap-feedback p-5 sm:p-6 ${feature.highlight
                                    ? 'border-emerald-500/30 bg-emerald-500/5'
                                    : ''
                                    }`}
                                style={{ opacity: 0 }}
                            >
                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 ${feature.highlight
                                    ? 'bg-emerald-500/20'
                                    : 'bg-neutral-800/50'
                                    }`}>
                                    <Icon className={`w-6 h-6 ${feature.highlight ? 'text-emerald-400' : 'text-neutral-400'
                                        }`} />
                                </div>
                                <h3 className="text-lg font-semibold text-white mb-2">
                                    {feature.title}
                                </h3>
                                <p className="text-neutral-400 text-sm leading-relaxed">
                                    {feature.description}
                                </p>
                                {feature.highlight && (
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
