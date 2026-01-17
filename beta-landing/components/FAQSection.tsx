"use client";

import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ChevronDown } from 'lucide-react';
import { faqs } from '@/data/constants';

if (typeof window !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
}

export function FAQSection() {
    const sectionRef = useRef<HTMLElement>(null);
    const headingRef = useRef<HTMLDivElement>(null);
    const faqsRef = useRef<HTMLDivElement>(null);
    const [openIndex, setOpenIndex] = useState<number | null>(null);

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

            const faqItems = faqsRef.current?.querySelectorAll('.faq-item');
            if (faqItems) {
                gsap.fromTo(
                    faqItems,
                    { opacity: 0, y: 20 },
                    {
                        opacity: 1,
                        y: 0,
                        duration: 0.5,
                        stagger: 0.1,
                        scrollTrigger: {
                            trigger: faqsRef.current,
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
            <div className="container max-w-3xl mx-auto">
                <div ref={headingRef} className="text-center mb-12" style={{ opacity: 0 }}>
                    <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold mb-4">
                        Frequently Asked <span className="text-emerald-400">Questions</span>
                    </h2>
                    <p className="text-neutral-400">
                        Got questions? We&apos;ve got answers.
                    </p>
                </div>

                <div ref={faqsRef} className="space-y-3">
                    {faqs.map((faq, index) => (
                        <div
                            key={index}
                            className="faq-item glass-card overflow-hidden"
                            style={{ opacity: 0 }}
                        >
                            <button
                                onClick={() => setOpenIndex(openIndex === index ? null : index)}
                                className="w-full p-5 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
                            >
                                <span className="font-medium text-white pr-4">{faq.question}</span>
                                <ChevronDown
                                    className={`w-5 h-5 text-neutral-400 transition-transform duration-200 flex-shrink-0 ${openIndex === index ? 'rotate-180' : ''
                                        }`}
                                />
                            </button>
                            <div
                                className={`overflow-hidden transition-all duration-200 ${openIndex === index ? 'max-h-40' : 'max-h-0'
                                    }`}
                            >
                                <p className="px-5 pb-5 text-neutral-400 text-sm leading-relaxed">
                                    {faq.answer}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
        </section>
    );
}
