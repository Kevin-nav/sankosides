"use client";

import { Navbar } from "@/components/navbar";

export default function TermsPage() {
    return (
        <div className="min-h-screen bg-neutral-950 text-neutral-200 selection:bg-emerald-500/30 font-sans">
            <Navbar />

            <main className="pt-32 pb-20 container px-4 md:px-6 max-w-3xl mx-auto">
                <h1 className="text-3xl font-bold text-white mb-8">Terms of Service</h1>

                <div className="prose prose-invert prose-emerald max-w-none space-y-8 text-neutral-400">
                    <p>Last updated: December 2025</p>

                    <section>
                        <h2 className="text-xl font-bold text-white mb-4">1. Acceptance of Terms</h2>
                        <p>
                            By accessing and using SankoSlides, you accept and agree to be bound by the terms and provision of this agreement.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-white mb-4">2. Use License</h2>
                        <p>
                            Permission is granted to temporarily download one copy of the materials (information or software) on SankoSlides' website for personal, non-commercial transitory viewing only.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-white mb-4">3. Disclaimer</h2>
                        <p>
                            The materials on SankoSlides' website are provided "as is". SankoSlides makes no warranties, expressed or implied, and hereby disclaims and negates all other warranties.
                        </p>
                    </section>
                </div>
            </main>
        </div>
    );
}
