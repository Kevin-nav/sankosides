"use client";

import { ReactNode } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Share2, Download } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface EditorLayoutProps {
    children: ReactNode;
    sidebar: ReactNode;
    title?: string;
}

export function EditorLayout({ children, sidebar, title = "Untitled Presentation" }: EditorLayoutProps) {
    return (
        <div className="flex h-screen w-full flex-col bg-black text-white overflow-hidden font-sans selection:bg-emerald-500/30">
            {/* Top Bar */}
            <header className="flex h-16 items-center justify-between border-b border-white/10 bg-neutral-950/50 px-6 backdrop-blur-md z-50">
                <div className="flex items-center gap-4">
                    <Link href="/dashboard">
                        <Button variant="ghost" size="icon" className="h-9 w-9 text-neutral-400 hover:text-white hover:bg-white/10 rounded-full transition-colors">
                            <ArrowLeft className="h-4 w-4" />
                        </Button>
                    </Link>
                    <div className="h-6 w-[1px] bg-white/10" />
                    <h1 className="text-sm font-semibold text-neutral-200 tracking-wide">{title}</h1>
                    <span className="rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
                        Draft
                    </span>
                </div>

                <div className="flex items-center gap-3">
                    <Button variant="ghost" size="sm" className="hidden md:flex h-8 text-xs font-medium text-neutral-400 hover:text-white hover:bg-white/5 transition-all">
                        <Share2 className="mr-2 h-3.5 w-3.5" />
                        Share
                    </Button>
                    <Button size="sm" className="h-8 bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs rounded-lg transition-all shadow-[0_0_15px_-3px_rgba(5,150,105,0.4)]">
                        <Download className="mr-2 h-3.5 w-3.5" />
                        Export
                    </Button>
                </div>
            </header>

            {/* Main Content Area */}
            <div className="flex flex-1 overflow-hidden">
                {/* Left Panel (Sidebar/Chat) */}
                <aside className="w-[400px] lg:w-[450px] xl:w-[500px] border-r border-white/10 bg-neutral-950 relative flex flex-col z-40 shadow-xl">
                    {sidebar}
                </aside>

                {/* Right Panel (Canvas/Preview) */}
                <main className="flex-1 bg-neutral-900/50 relative overflow-hidden flex flex-col items-center justify-center p-8">
                    <div className="absolute inset-0 z-0 opacity-20 pointer-events-none">
                        <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
                        <div className="absolute inset-0 bg-gradient-to-t from-neutral-950 via-transparent to-transparent"></div>
                    </div>

                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="relative z-10 w-full max-w-[90%] lg:max-w-[1280px] aspect-video rounded-xl border border-white/5 bg-neutral-950 shadow-2xl shadow-black/50 overflow-hidden ring-1 ring-white/10"
                    >
                        {children}
                    </motion.div>
                </main>
            </div>
        </div>
    );
}
