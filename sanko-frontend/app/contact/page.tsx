"use client";

import { Navbar } from "@/components/navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { motion } from "framer-motion";
import { Mail, MessageSquare, Send } from "lucide-react";

export default function ContactPage() {
    return (
        <div className="min-h-screen bg-neutral-950 text-neutral-200 selection:bg-emerald-500/30 font-sans">
            <Navbar />

            <main className="pt-32 pb-20">
                <section className="container px-4 md:px-6 mb-16 text-center">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="max-w-2xl mx-auto space-y-4"
                    >
                        <h1 className="text-4xl md:text-5xl font-bold tracking-tight text-white">
                            Get in touch
                        </h1>
                        <p className="text-lg text-neutral-400">
                            Have a question about the platform? We're here to help.
                        </p>
                    </motion.div>
                </section>

                <section className="container px-4 md:px-6 max-w-lg mx-auto">
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5, delay: 0.1 }}
                        className="bg-neutral-900 border border-neutral-800 rounded-3xl p-8 shadow-2xl"
                    >
                        <form className="space-y-6">
                            <div className="space-y-2">
                                <Label htmlFor="name" className="text-neutral-300">Name</Label>
                                <Input id="name" placeholder="Your name" className="bg-neutral-950 border-neutral-800 focus-visible:ring-emerald-500/50" />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="email" className="text-neutral-300">Email</Label>
                                <Input id="email" type="email" placeholder="you@university.edu" className="bg-neutral-950 border-neutral-800 focus-visible:ring-emerald-500/50" />
                            </div>

                            <div className="space-y-2">
                                <Label htmlFor="message" className="text-neutral-300">Message</Label>
                                <Textarea id="message" placeholder="How can we help?" className="min-h-[150px] bg-neutral-950 border-neutral-800 focus-visible:ring-emerald-500/50" />
                            </div>

                            <Button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-medium h-11">
                                <Send className="mr-2 h-4 w-4" /> Send Message
                            </Button>
                        </form>

                        <div className="mt-8 flex flex-col items-center space-y-4 text-center">
                            <div className="text-sm text-neutral-500">Or email us directly</div>
                            <a href="mailto:support@sankoslides.com" className="flex items-center gap-2 text-white hover:text-emerald-400 transition-colors bg-neutral-800/50 px-4 py-2 rounded-full border border-neutral-700">
                                <Mail className="h-4 w-4" /> support@sankoslides.com
                            </a>
                        </div>
                    </motion.div>
                </section>
            </main>
        </div>
    );
}
