"use client";

import Link from "next/link";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { ArrowRight, Sparkles, Terminal, FileText, Bot, MoveRight, CheckCircle2, Layout, Zap, GraduationCap } from "lucide-react";
import { motion } from "framer-motion";

export default function Home() {
    const fadeInUp = {
        initial: { opacity: 0, y: 20 },
        animate: { opacity: 1, y: 0 },
        transition: { duration: 0.5 }
    };

    const staggerContainer = {
        animate: {
            transition: {
                staggerChildren: 0.1
            }
        }
    };

    return (
        <div className="flex flex-col min-h-screen overflow-hidden bg-neutral-950 font-sans selection:bg-emerald-500/30">
            <main className="flex-1">
                {/* Dynamic Background */}
                <div className="fixed inset-0 z-0 pointer-events-none">
                    <div className="absolute top-[-20%] left-[20%] w-[600px] h-[600px] bg-emerald-500/10 blur-[120px] rounded-full mix-blend-screen animate-pulse duration-[4000ms]" />
                    <div className="absolute bottom-[-10%] right-[10%] w-[500px] h-[500px] bg-teal-500/10 blur-[100px] rounded-full mix-blend-screen" />
                </div>

                {/* Hero Section */}
                <section className="relative w-full pt-32 pb-20 md:pt-40 md:pb-32 lg:pt-48 lg:pb-40">
                    <div className="container relative z-10 px-4 md:px-6">
                        <motion.div
                            className="flex flex-col items-center text-center space-y-10 max-w-4xl mx-auto"
                            initial="initial"
                            animate="animate"
                            variants={staggerContainer}
                        >
                            <motion.div variants={fadeInUp} className="inline-flex items-center rounded-full border border-emerald-500/30 bg-emerald-500/10 px-4 py-1.5 text-sm font-medium text-emerald-400 backdrop-blur-md shadow-lg shadow-emerald-900/20 hover:bg-emerald-500/20 transition-colors cursor-default">
                                <Sparkles className="mr-2 h-4 w-4 animate-pulse" />
                                <span>The future of academic presentations</span>
                            </motion.div>

                            <motion.div variants={fadeInUp} className="space-y-6">
                                <h1 className="text-5xl md:text-7xl font-bold tracking-tighter bg-clip-text text-transparent bg-gradient-to-b from-white via-white to-neutral-400 pb-2 leading-[1.1]">
                                    Stop Formatting. <br />
                                    Start <span className="text-emerald-500 bg-emerald-500/10 px-4 rounded-xl inline-block mt-2">Presenting.</span>
                                </h1>
                                <p className="mx-auto max-w-[700px] text-neutral-400 md:text-xl font-light leading-relaxed">
                                    SankoSlides transforms your handwritten notes, PDFs, and raw ideas into stunning, university-grade presentations.
                                    No more late nights wrestling with slide layouts.
                                </p>
                            </motion.div>

                            <motion.div variants={fadeInUp} className="flex flex-col sm:flex-row gap-4 items-center w-full justify-center">
                                <Button size="lg" className="group h-14 px-8 bg-emerald-600 hover:bg-emerald-500 text-white rounded-full text-lg shadow-[0_0_40px_-10px_rgba(16,185,129,0.4)] hover:shadow-[0_0_60px_-10px_rgba(16,185,129,0.6)] transition-all hover:scale-105" asChild>
                                    <Link href="/register">
                                        Create Your First Deck <MoveRight className="ml-2 h-5 w-5 group-hover:translate-x-1 transition-transform" />
                                    </Link>
                                </Button>
                                <Button variant="ghost" size="lg" className="h-14 px-8 text-neutral-400 hover:text-white hover:bg-white/5 rounded-full text-lg" asChild>
                                    <Link href="/login">Explore the Gallery</Link>
                                </Button>
                            </motion.div>
                        </motion.div>

                        {/* Hero Visual */}
                        <motion.div
                            className="mt-20 relative mx-auto w-full max-w-5xl aspect-[16/9] group perspective-1000"
                            initial={{ opacity: 0, scale: 0.95, y: 40 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            transition={{ delay: 0.4, duration: 0.8 }}
                        >
                            <div className="absolute -inset-1 bg-gradient-to-r from-emerald-500/30 to-teal-500/30 rounded-2xl blur-xl opacity-50 group-hover:opacity-75 transition duration-1000 animate-pulse-slow" />
                            <div className="relative h-full w-full rounded-2xl overflow-hidden border border-neutral-800 bg-neutral-900 shadow-2xl transition-transform duration-700">
                                <Image
                                    src="/images/hero.png"
                                    alt="Transformation from notes to slides"
                                    fill
                                    className="object-cover"
                                    priority
                                />
                                {/* Glass Overlay UI - Subtle shine */}
                                <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-700 pointer-events-none" />
                                <div className="absolute bottom-0 left-0 right-0 h-1/2 bg-gradient-to-t from-neutral-950 via-neutral-950/60 to-transparent" />
                            </div>
                        </motion.div>
                    </div>
                </section>

                {/* Vision/Features Section */}
                <section className="relative w-full py-32 border-t border-white/5 bg-neutral-950/30 backdrop-blur-sm">
                    <div className="container px-4 md:px-6">
                        <motion.div
                            className="text-center mb-20 space-y-4"
                            initial={{ opacity: 0, y: 20 }}
                            whileInView={{ opacity: 1, y: 0 }}
                            viewport={{ once: true }}
                            transition={{ duration: 0.5 }}
                        >
                            <h2 className="text-3xl md:text-5xl font-bold text-white">Three Ways We Give You <span className="text-emerald-500">Time Back.</span></h2>
                            <p className="text-neutral-400 max-w-2xl mx-auto text-lg leading-relaxed">
                                We don't just format slides. We understand your research and structure it for you.
                            </p>
                        </motion.div>

                        <div className="grid gap-8 md:grid-cols-3">
                            {/* Feature 1 */}
                            <motion.div
                                className="group relative p-8 rounded-3xl border border-white/5 bg-neutral-900/40 hover:bg-neutral-900/60 transition-all duration-500 hover:border-emerald-500/30 overflow-hidden flex flex-col"
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5, delay: 0.1 }}
                                whileHover={{ y: -5 }}
                            >
                                <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                <div className="relative z-10 space-y-4 flex-1">
                                    <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 flex items-center justify-center border border-emerald-500/30 group-hover:scale-110 transition-transform duration-500">
                                        <Layout className="h-6 w-6 text-emerald-400" />
                                    </div>
                                    <h3 className="text-xl font-bold text-white">Visuals, Instantly.</h3>
                                    <p className="text-neutral-400 leading-relaxed">
                                        Snap a photo of your whiteboard sketch or upload a legacy slide. We recreate it as pixel-perfect, editable elements.
                                    </p>
                                </div>
                                <div className="mt-8 pt-8 border-t border-white/5 relative h-32 w-full overflow-hidden rounded-lg opacity-50 group-hover:opacity-100 transition-opacity">
                                    <div className="absolute inset-0 bg-gradient-to-tr from-emerald-500/20 to-transparent" />
                                    {/* Abstract visual rep */}
                                    <div className="absolute bottom-2 left-2 right-2 top-2 border border-emerald-500/20 rounded-md backdrop-blur-sm grid grid-cols-2 gap-2 p-2">
                                        <div className="bg-emerald-500/10 rounded h-full animate-pulse" />
                                        <div className="space-y-2">
                                            <div className="h-2 bg-emerald-500/20 rounded w-full" />
                                            <div className="h-2 bg-emerald-500/20 rounded w-2/3" />
                                        </div>
                                    </div>
                                </div>
                            </motion.div>

                            {/* Feature 2 */}
                            <motion.div
                                className="group relative p-8 rounded-3xl border border-white/5 bg-neutral-900/40 hover:bg-neutral-900/60 transition-all duration-500 hover:border-emerald-500/30 overflow-hidden flex flex-col"
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5, delay: 0.2 }}
                                whileHover={{ y: -5 }}
                            >
                                <div className="absolute inset-0 bg-gradient-to-br from-purple-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                <div className="relative z-10 space-y-4 flex-1">
                                    <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 flex items-center justify-center border border-purple-500/30 group-hover:scale-110 transition-transform duration-500">
                                        <Zap className="h-6 w-6 text-purple-400" />
                                    </div>
                                    <h3 className="text-xl font-bold text-white">Chaos to Order.</h3>
                                    <p className="text-neutral-400 leading-relaxed">
                                        Dump your messy PDFs, Word docs, and loose notes. We extract the key arguments and structure them into a coherent narrative.
                                    </p>
                                </div>
                                <div className="mt-6 rounded-xl overflow-hidden border border-white/5 aspect-[4/3] relative">
                                    <Image src="/images/feature_synthesis.png" alt="Synthesis" fill className="object-cover opacity-60 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500" />
                                </div>
                            </motion.div>

                            {/* Feature 3 */}
                            <motion.div
                                className="group relative p-8 rounded-3xl border border-white/5 bg-neutral-900/40 hover:bg-neutral-900/60 transition-all duration-500 hover:border-emerald-500/30 overflow-hidden flex flex-col"
                                initial={{ opacity: 0, y: 20 }}
                                whileInView={{ opacity: 1, y: 0 }}
                                viewport={{ once: true }}
                                transition={{ duration: 0.5, delay: 0.3 }}
                                whileHover={{ y: -5 }}
                            >
                                <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                                <div className="relative z-10 space-y-4 flex-1">
                                    <div className="h-12 w-12 rounded-2xl bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center border border-blue-500/30 group-hover:scale-110 transition-transform duration-500">
                                        <GraduationCap className="h-6 w-6 text-blue-400" />
                                    </div>
                                    <h3 className="text-xl font-bold text-white">Your Research Partner.</h3>
                                    <p className="text-neutral-400 leading-relaxed">
                                        Stuck on a topic? Our agents research the web for you, finding credible sources to back up your claims.
                                    </p>
                                </div>
                                <div className="mt-6 rounded-xl overflow-hidden border border-white/5 aspect-[4/3] relative">
                                    <Image src="/images/feature_research.png" alt="Research" fill className="object-cover opacity-60 group-hover:opacity-100 group-hover:scale-105 transition-all duration-500" />
                                </div>
                            </motion.div>
                        </div>
                    </div>
                </section>

                {/* CTA Section */}
                <section className="py-24 relative overflow-hidden">
                    <div className="absolute inset-0 bg-emerald-900/5" />
                    <div className="container px-4 relative z-10 text-center">
                        <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">Ready to ace your presentation?</h2>
                        <p className="text-xl text-neutral-400 mb-10 max-w-2xl mx-auto">Join thousands of students who are reclaiming their study time.</p>
                        <Button size="lg" className="h-14 px-10 bg-white text-neutral-950 hover:bg-neutral-200 rounded-full text-lg font-bold shadow-2xl hover:scale-105 transition-transform" asChild>
                            <Link href="/register">Get Started Now</Link>
                        </Button>
                    </div>
                </section>

            </main>

            {/* Enhanced Footer */}
            <footer className="w-full py-16 border-t border-white/5 bg-neutral-950 text-neutral-400">
                <div className="container px-4 md:px-6">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-10 mb-16">
                        <div className="col-span-2 md:col-span-1 space-y-4">
                            <div className="flex items-center gap-2 mb-4">
                                <div className="h-8 w-8 rounded bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30">
                                    <Sparkles className="h-4 w-4 text-emerald-400" />
                                </div>
                                <span className="font-bold text-white tracking-tight">SankoSlides</span>
                            </div>
                            <p className="text-sm leading-relaxed text-neutral-500">
                                The AI-powered presentation suite built for the modern student.
                            </p>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-white font-medium">Product</h4>
                            <ul className="space-y-3 text-sm">
                                <li><Link href="/pricing" className="hover:text-emerald-500 transition-colors">Pricing</Link></li>
                                <li><Link href="#" className="hover:text-emerald-500 transition-colors">Replica Engine</Link></li>
                                <li><Link href="#" className="hover:text-emerald-500 transition-colors">Synthesis</Link></li>
                            </ul>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-white font-medium">Resources</h4>
                            <ul className="space-y-3 text-sm">
                                <li><Link href="#" className="hover:text-emerald-500 transition-colors">Blog</Link></li>
                                <li><Link href="#" className="hover:text-emerald-500 transition-colors">Community</Link></li>
                                <li><Link href="#" className="hover:text-emerald-500 transition-colors">Help Center</Link></li>
                            </ul>
                        </div>

                        <div className="space-y-4">
                            <h4 className="text-white font-medium">Company</h4>
                            <ul className="space-y-3 text-sm">
                                <li><Link href="/about" className="hover:text-emerald-500 transition-colors">About Us</Link></li>
                                <li><Link href="#" className="hover:text-emerald-500 transition-colors">Careers</Link></li>
                                <li><Link href="/contact" className="hover:text-emerald-500 transition-colors">Contact</Link></li>
                            </ul>
                        </div>
                    </div>

                    <div className="pt-8 border-t border-white/5 flex flex-col md:flex-row justify-between items-center gap-4">
                        <p className="text-sm text-neutral-600">© 2025 SankoSlides Inc. All rights reserved.</p>
                        <div className="flex gap-6">
                            <Link className="text-sm text-neutral-600 hover:text-emerald-500 transition-colors" href="/privacy">Privacy Policy</Link>
                            <Link className="text-sm text-neutral-600 hover:text-emerald-500 transition-colors" href="/terms">Terms of Service</Link>
                        </div>
                    </div>
                </div>
            </footer>
        </div>
    );
}