import { useState, useRef, useEffect } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ChevronDown } from 'lucide-react';
import { faqs } from '../data/constants';

gsap.registerPlugin(ScrollTrigger);

export function FAQSection() {
    const sectionRef = useRef<HTMLElement>(null);
    const headingRef = useRef<HTMLHeadingElement>(null);
    const itemsRef = useRef<HTMLDivElement>(null);
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

            const items = itemsRef.current?.querySelectorAll('.faq-item');
            if (items) {
                gsap.fromTo(
                    items,
                    { opacity: 0, y: 20 },
                    {
                        opacity: 1,
                        y: 0,
                        duration: 0.5,
                        stagger: 0.1,
                        scrollTrigger: {
                            trigger: itemsRef.current,
                            start: 'top 75%',
                            toggleActions: 'play none none reverse',
                        },
                    }
                );
            }
        }, sectionRef);

        return () => ctx.revert();
    }, []);

    const toggleFaq = (index: number) => {
        setOpenIndex(openIndex === index ? null : index);
    };

    return (
        <section
            ref={sectionRef}
            className="py-16 sm:py-24 px-4 sm:px-6 lg:px-8"
        >
            <div className="container max-w-3xl mx-auto">
                <h2
                    ref={headingRef}
                    className="text-2xl sm:text-3xl md:text-4xl font-bold text-center mb-10 sm:mb-12"
                    style={{ opacity: 0 }}
                >
                    Frequently Asked <span className="text-emerald-400">Questions</span>
                </h2>

                <div ref={itemsRef} className="space-y-3">
                    {faqs.map((faq, index) => (
                        <div
                            key={index}
                            className="faq-item rounded-xl border border-neutral-800 overflow-hidden"
                            style={{ opacity: 0 }}
                        >
                            <button
                                onClick={() => toggleFaq(index)}
                                className="w-full flex items-center justify-between p-4 sm:p-5 text-left bg-neutral-900/50 hover:bg-neutral-800/50 transition-colors"
                            >
                                <span className="font-medium text-white pr-4">{faq.question}</span>
                                <ChevronDown
                                    className={`w-5 h-5 text-neutral-400 flex-shrink-0 transition-transform duration-200 ${openIndex === index ? 'rotate-180' : ''
                                        }`}
                                />
                            </button>
                            <div
                                className={`overflow-hidden transition-all duration-300 ${openIndex === index ? 'max-h-48' : 'max-h-0'
                                    }`}
                            >
                                <p className="p-4 sm:p-5 pt-0 text-neutral-400 text-sm sm:text-base">
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
