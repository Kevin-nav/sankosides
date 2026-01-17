"use client";

import { useRef, useEffect, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { Sparkles } from 'lucide-react';

// Register GSAP plugins
if (typeof window !== 'undefined') {
    gsap.registerPlugin(ScrollTrigger);
}

interface NavbarProps {
    onCtaClick: () => void;
}

export function Navbar({ onCtaClick }: NavbarProps) {
    const navRef = useRef<HTMLElement>(null);
    const [scrolled, setScrolled] = useState(false);

    useEffect(() => {
        // Entrance animation
        gsap.fromTo(
            navRef.current,
            { opacity: 0, y: -20 },
            { opacity: 1, y: 0, duration: 0.6, ease: 'power2.out' }
        );

        // Scroll effect
        const handleScroll = () => {
            setScrolled(window.scrollY > 50);
        };
        window.addEventListener('scroll', handleScroll);
        return () => window.removeEventListener('scroll', handleScroll);
    }, []);

    return (
        <nav
            ref={navRef}
            className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${scrolled
                    ? 'bg-neutral-950/90 backdrop-blur-lg border-b border-white/5'
                    : 'bg-transparent'
                }`}
            style={{ opacity: 0 }}
        >
            <div className="container max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex items-center justify-between h-16 sm:h-20">
                    {/* Logo */}
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30">
                            <Sparkles className="w-4 h-4 text-emerald-400" />
                        </div>
                        <span className="text-lg font-bold text-white tracking-tight">
                            SankoSlides
                        </span>
                        <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider">
                            Beta
                        </span>
                    </div>

                    {/* CTA Button */}
                    <button
                        onClick={onCtaClick}
                        className="px-4 sm:px-6 py-2 sm:py-2.5 rounded-full bg-emerald-500 text-white font-semibold text-sm hover:bg-emerald-400 transition-colors shadow-lg shadow-emerald-500/20"
                    >
                        Join Beta
                    </button>
                </div>
            </div>
        </nav>
    );
}
