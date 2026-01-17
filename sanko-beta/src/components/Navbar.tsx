import { Sparkles } from 'lucide-react';

interface NavbarProps {
    onCtaClick: () => void;
}

export function Navbar({ onCtaClick }: NavbarProps) {
    return (
        <nav className="fixed top-0 left-0 right-0 z-40 bg-neutral-950/80 backdrop-blur-lg border-b border-neutral-800/50">
            <div className="container flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8 mx-auto max-w-6xl">
                {/* Logo */}
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-white" />
                    </div>
                    <span className="font-bold text-white text-lg">SankoSlides</span>
                    <span className="hidden sm:inline-block px-2 py-0.5 text-xs font-medium bg-emerald-500/10 text-emerald-400 rounded-full border border-emerald-500/20">
                        BETA
                    </span>
                </div>

                {/* CTA */}
                <button
                    onClick={onCtaClick}
                    className="btn btn-primary text-sm py-2 px-4"
                >
                    Join Beta
                </button>
            </div>
        </nav>
    );
}
