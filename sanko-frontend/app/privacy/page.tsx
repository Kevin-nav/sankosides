"use client";

import { Navbar } from "@/components/navbar";

export default function PrivacyPage() {
    return (
        <div className="min-h-screen bg-neutral-950 text-neutral-200 selection:bg-emerald-500/30 font-sans">
            <Navbar />

            <main className="pt-32 pb-20 container px-4 md:px-6 max-w-3xl mx-auto">
                <h1 className="text-3xl font-bold text-white mb-8">Privacy Policy</h1>

                <div className="prose prose-invert prose-emerald max-w-none space-y-8 text-neutral-400">
                    <p>Last updated: December 2025</p>

                    <section>
                        <h2 className="text-xl font-bold text-white mb-4">1. Introduction</h2>
                        <p>
                            SankoSlides ("we", "our", or "us") respects your privacy. This Privacy Policy explains how we collect, use, and protect your information when you use our services.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-white mb-4">2. Data We Collect</h2>
                        <ul className="list-disc pl-5 space-y-2">
                            <li>Account information (email, name) provided during registration.</li>
                            <li>Content you upload (notes, PDFs) for slide generation.</li>
                            <li>Usage data (features used, time spent) to improve our service.</li>
                        </ul>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-white mb-4">3. How We Use Your Data</h2>
                        <p>
                            We use your content solely to provide the presentation generation service. We do not sell your personal data or uploaded content to third parties.
                        </p>
                    </section>

                    <section>
                        <h2 className="text-xl font-bold text-white mb-4">4. Contact Us</h2>
                        <p>
                            If you have questions about this policy, please contact us at <a href="mailto:privacy@sankoslides.com" className="text-emerald-500 hover:underline">privacy@sankoslides.com</a>.
                        </p>
                    </section>
                </div>
            </main>
        </div>
    );
}
