"use client";

import { useEffect, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Sparkles, Heart } from 'lucide-react';

if (typeof window !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
}

export function Footer() {
    const footerRef = useRef<HTMLElement>(null);

    useEffect(() => {
        const ctx = gsap.context(() => {
            gsap.fromTo(
                footerRef.current,
                { opacity: 0 },
                {
                    opacity: 1,
                    duration: 0.6,
                    scrollTrigger: {
                        trigger: footerRef.current,
                        start: 'top 90%',
                        toggleActions: 'play none none reverse',
                    },
                }
            );
        }, footerRef);

        return () => ctx.revert();
    }, []);

    return (
        <footer
            ref={footerRef}
            className="py-12 px-4 sm:px-6 lg:px-8 border-t border-white/5"
            style={{ opacity: 0 }}
        >
            <div className="container max-w-5xl mx-auto">
                <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    {/* Logo */}
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30">
                            <Sparkles className="w-4 h-4 text-emerald-400" />
                        </div>
                        <span className="text-lg font-bold text-white tracking-tight">
                            SankoSlides
                        </span>
                    </div>

                    {/* Contact Email */}
                    <a
                        href="mailto:info@sankoslides.com"
                        className="flex items-center gap-2 text-neutral-400 text-sm hover:text-emerald-400 transition-colors"
                    >
                        <span>info@sankoslides.com</span>
                    </a>

                    {/* Made in Ghana */}
                    <div className="flex items-center gap-2 text-neutral-500 text-sm">
                        <span>Made with</span>
                        <Heart className="w-4 h-4 text-red-500 fill-current" />
                        <span>in Ghana 🇬🇭</span>
                    </div>

                    {/* Copyright */}
                    <p className="text-neutral-600 text-sm">
                        © 2026 SankoSlides by HCX Technologies. All rights reserved.
                    </p>
                </div>
            </div>
        </footer>
    );
}
