"use client";

import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import Link from "next/link";
import { Check, Sparkles } from "lucide-react";

export default function PricingPage() {
    return (
        <div className="min-h-screen bg-neutral-950 text-neutral-200 selection:bg-emerald-500/30 font-sans">
            <Navbar />

            <main className="pt-32 pb-20">
                <section className="container px-4 md:px-6 mb-16 text-center">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                    >
                        <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white mb-4">
                            Transparent Pricing
                        </h1>
                        <p className="text-xl text-neutral-400">
                            Start for free. Upgrade for superpowers.
                        </p>
                    </motion.div>
                </section>

                <section className="container px-4 md:px-6 max-w-5xl mx-auto">
                    <div className="grid md:grid-cols-2 gap-8 items-start">
                        {/* Free Tier */}
                        <div className="p-8 rounded-3xl border border-white/5 bg-neutral-900/40">
                            <h3 className="text-2xl font-bold text-white mb-2">Student Basic</h3>
                            <div className="text-4xl font-bold text-white mb-6">$0<span className="text-lg text-neutral-500 font-normal">/mo</span></div>
                            <p className="text-neutral-400 mb-8">Perfect for your first few assignments.</p>

                            <ul className="space-y-4 mb-8">
                                <li className="flex items-center gap-3 text-neutral-300">
                                    <Check className="h-5 w-5 text-neutral-500" /> 3 Presentations / month
                                </li>
                                <li className="flex items-center gap-3 text-neutral-300">
                                    <Check className="h-5 w-5 text-neutral-500" /> Basic Templates
                                </li>
                                <li className="flex items-center gap-3 text-neutral-300">
                                    <Check className="h-5 w-5 text-neutral-500" /> PDF Export
                                </li>
                            </ul>

                            <Button variant="outline" className="w-full h-12 rounded-full bg-transparent border-neutral-700 hover:bg-neutral-800 text-white" asChild>
                                <Link href="/register">Get Started</Link>
                            </Button>
                        </div>

                        {/* Pro Tier */}
                        <div className="relative p-8 rounded-3xl border border-emerald-500/30 bg-neutral-900/80 shadow-[0_0_40px_-10px_rgba(16,185,129,0.2)]">
                            <div className="absolute top-0 right-0 p-4">
                                <span className="bg-emerald-500/10 text-emerald-400 text-xs font-bold px-3 py-1 rounded-full border border-emerald-500/20">MOST POPULAR</span>
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-2">Researcher Pro</h3>
                            <div className="text-4xl font-bold text-white mb-6">$12<span className="text-lg text-neutral-500 font-normal">/mo</span></div>
                            <p className="text-neutral-400 mb-8">For serious students and PhD candidates.</p>

                            <ul className="space-y-4 mb-8">
                                <li className="flex items-center gap-3 text-white font-medium">
                                    <div className="p-1 rounded bg-emerald-500/20"><Check className="h-3 w-3 text-emerald-500" /></div>
                                    Unlimited Presentations
                                </li>
                                <li className="flex items-center gap-3 text-white font-medium">
                                    <div className="p-1 rounded bg-emerald-500/20"><Check className="h-3 w-3 text-emerald-500" /></div>
                                    Deep Research Agent (Web Access)
                                </li>
                                <li className="flex items-center gap-3 text-white font-medium">
                                    <div className="p-1 rounded bg-emerald-500/20"><Check className="h-3 w-3 text-emerald-500" /></div>
                                    LaTeX & PowerPoint Export
                                </li>
                                <li className="flex items-center gap-3 text-white font-medium">
                                    <div className="p-1 rounded bg-emerald-500/20"><Check className="h-3 w-3 text-emerald-500" /></div>
                                    Custom University Themes
                                </li>
                            </ul>

                            <Button className="w-full h-12 rounded-full bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-900/20" asChild>
                                <Link href="/register">Upgrade to Pro</Link>
                            </Button>
                        </div>
                    </div>
                </section>
            </main>
        </div>
    );
}
