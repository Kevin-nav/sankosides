import { Sparkles, Twitter, Instagram, Linkedin, Heart } from 'lucide-react';

export function Footer() {
    const currentYear = new Date().getFullYear();

    return (
        <footer className="py-12 px-4 sm:px-6 lg:px-8 border-t border-neutral-800/50">
            <div className="container max-w-6xl mx-auto">
                <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    {/* Logo */}
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-lg bg-emerald-500 flex items-center justify-center">
                            <Sparkles className="w-4 h-4 text-white" />
                        </div>
                        <span className="font-bold text-white">SankoSlides</span>
                    </div>

                    {/* Links */}
                    <div className="flex items-center gap-6 text-sm text-neutral-400">
                        <a href="#" className="hover:text-white transition-colors tap-feedback">
                            About
                        </a>
                        <a href="#" className="hover:text-white transition-colors tap-feedback">
                            Contact
                        </a>
                        <a href="#" className="hover:text-white transition-colors tap-feedback">
                            Privacy
                        </a>
                    </div>

                    {/* Social links */}
                    <div className="flex items-center gap-3">
                        <a
                            href="#"
                            className="w-9 h-9 rounded-lg bg-neutral-800/50 flex items-center justify-center text-neutral-400 hover:text-white hover:bg-neutral-700 transition-colors tap-feedback"
                            aria-label="Twitter"
                        >
                            <Twitter className="w-4 h-4" />
                        </a>
                        <a
                            href="#"
                            className="w-9 h-9 rounded-lg bg-neutral-800/50 flex items-center justify-center text-neutral-400 hover:text-white hover:bg-neutral-700 transition-colors tap-feedback"
                            aria-label="Instagram"
                        >
                            <Instagram className="w-4 h-4" />
                        </a>
                        <a
                            href="#"
                            className="w-9 h-9 rounded-lg bg-neutral-800/50 flex items-center justify-center text-neutral-400 hover:text-white hover:bg-neutral-700 transition-colors tap-feedback"
                            aria-label="LinkedIn"
                        >
                            <Linkedin className="w-4 h-4" />
                        </a>
                    </div>
                </div>

                {/* Bottom section */}
                <div className="mt-8 pt-8 border-t border-neutral-800/50">
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                        <p className="text-sm text-neutral-500">
                            © {currentYear} SankoSlides. Built for Ghanaian students.
                        </p>

                        {/* Made in Ghana badge */}
                        <div className="flex items-center gap-2 text-sm text-neutral-500">
                            <span>Made with</span>
                            <Heart className="w-4 h-4 text-red-400 fill-red-400" />
                            <span>in Ghana</span>
                            <span className="text-lg" role="img" aria-label="Ghana flag">🇬🇭</span>
                        </div>
                    </div>
                </div>
            </div>
        </footer>
    );
}
