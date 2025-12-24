"use client";

import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import Link from "next/link";
import { ArrowRight, BookOpen, Users, Zap } from "lucide-react";

export default function AboutPage() {
    return (
        <div className="min-h-screen bg-neutral-950 text-neutral-200 selection:bg-emerald-500/30 font-sans">
            <Navbar />

            <main className="pt-32 pb-20">
                {/* Hero */}
                <section className="container px-4 md:px-6 mb-24">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="max-w-3xl mx-auto text-center space-y-6"
                    >
                        <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-white">
                            We build for the <span className="text-emerald-500">midnight scholars.</span>
                        </h1>
                        <p className="text-xl text-neutral-400 leading-relaxed">
                            SankoSlides was born in a dorm room at 3 AM. We realized that students spend more time formatting slides than understanding their research. We're here to flip that equation.
                        </p>
                    </motion.div>
                </section>

                {/* Values Grid */}
                <section className="container px-4 md:px-6 mb-24">
                    <div className="grid md:grid-cols-3 gap-8">
                        <motion.div
                            whileHover={{ y: -5 }}
                            className="p-8 rounded-3xl bg-neutral-900/40 border border-white/5 space-y-4"
                        >
                            <div className="h-12 w-12 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                                <Zap className="h-6 w-6 text-emerald-400" />
                            </div>
                            <h3 className="text-xl font-bold text-white">Speed is Intelligence</h3>
                            <p className="text-neutral-400">
                                Tools should move as fast as your thoughts. Waiting for layout adjustments breaks the flow state.
                            </p>
                        </motion.div>
                        <motion.div
                            whileHover={{ y: -5 }}
                            className="p-8 rounded-3xl bg-neutral-900/40 border border-white/5 space-y-4"
                        >
                            <div className="h-12 w-12 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
                                <BookOpen className="h-6 w-6 text-purple-400" />
                            </div>
                            <h3 className="text-xl font-bold text-white">Academic Rigor</h3>
                            <p className="text-neutral-400">
                                We respect the citation. Our AI is tuned for academic integrity, not just generating fluff.
                            </p>
                        </motion.div>
                        <motion.div
                            whileHover={{ y: -5 }}
                            className="p-8 rounded-3xl bg-neutral-900/40 border border-white/5 space-y-4"
                        >
                            <div className="h-12 w-12 rounded-xl bg-blue-500/10 flex items-center justify-center border border-blue-500/20">
                                <Users className="h-6 w-6 text-blue-400" />
                            </div>
                            <h3 className="text-xl font-bold text-white">Student First</h3>
                            <p className="text-neutral-400">
                                Priced for a student budget. Built for a student workflow. No enterprise bloat.
                            </p>
                        </motion.div>
                    </div>
                </section>

                {/* CTA */}
                <section className="container px-4 text-center">
                    <div className="max-w-2xl mx-auto p-12 rounded-3xl bg-gradient-to-br from-emerald-900/20 to-neutral-900/50 border border-emerald-500/10">
                        <h2 className="text-3xl font-bold text-white mb-6">Join the movement.</h2>
                        <Button className="bg-emerald-600 hover:bg-emerald-500 text-white rounded-full px-8 h-12" asChild>
                            <Link href="/register">Start Creating Free <ArrowRight className="ml-2 h-4 w-4" /></Link>
                        </Button>
                    </div>
                </section>
            </main>
        </div>
    );
}
