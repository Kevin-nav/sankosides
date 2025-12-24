"use client";

import { useAuth } from "@/components/auth-provider";
import { DashboardNav } from "@/components/dashboard/nav";
import { UserNav } from "@/components/dashboard/user-nav";
import { LayoutDashboard, FileText, Settings, Menu } from "lucide-react";
import { motion } from "framer-motion";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";

export const dashboardConfig = {
    sidebarNav: [
        {
            title: "Projects",
            href: "/dashboard",
            icon: LayoutDashboard,
        },
        {
            title: "Templates",
            href: "/dashboard/templates",
            icon: FileText,
        },
        {
            title: "Settings",
            href: "/dashboard/settings",
            icon: Settings,
        },
    ],
};

interface DashboardShellProps {
    children: React.ReactNode;
}

export function DashboardShell({ children }: DashboardShellProps) {
    const { user } = useAuth();

    return (
        <div className="flex min-h-screen flex-col space-y-6 bg-background text-foreground selection:bg-primary/30">
            <header className="sticky top-0 z-40 border-b border-border bg-background/80 backdrop-blur-md">
                <div className="container flex h-16 items-center justify-between py-4 px-4 md:px-6">

                    <div className="flex gap-6 md:gap-10">
                        {/* Mobile Menu */}
                        <Sheet>
                            <SheetTrigger asChild>
                                <Button variant="ghost" className="px-0 text-base hover:bg-transparent focus-visible:bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 md:hidden ml-2">
                                    <Menu className="h-6 w-6 text-foreground" />
                                    <span className="sr-only">Toggle Menu</span>
                                </Button>
                            </SheetTrigger>
                            <SheetContent side="left" className="pr-0 pt-10 bg-background border-r-border text-foreground w-[300px] sm:w-[400px]">
                                <div className="px-7">
                                    <a href="/" className="flex items-center space-x-2">
                                        <div className="h-6 w-6 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-[0_0_15px_-4px_rgba(16,185,129,0.5)]" />
                                        <span className="font-bold text-foreground tracking-tight">
                                            SankoSlides
                                        </span>
                                    </a>
                                </div>
                                <div className="mt-8 px-4">
                                    <DashboardNav items={dashboardConfig.sidebarNav} />
                                </div>
                            </SheetContent>
                        </Sheet>

                        <a href="/" className="flex items-center space-x-2 hidden md:flex">
                            <div className="h-6 w-6 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 shadow-[0_0_15px_-4px_rgba(16,185,129,0.5)]" />
                            <span className="hidden font-bold text-foreground sm:inline-block tracking-tight">
                                SankoSlides
                            </span>
                        </a>
                    </div>
                    <UserNav />
                </div>
            </header>
            <div className="container grid flex-1 gap-12 md:grid-cols-[200px_1fr]">
                <aside className="hidden w-[200px] flex-col md:flex border-r border-border pr-6 sticky top-20 h-[calc(100vh-5rem)] overflow-y-auto">
                    <DashboardNav items={dashboardConfig.sidebarNav} />
                </aside>
                <main className="flex w-full flex-1 flex-col overflow-hidden py-6 px-4 md:px-6">
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.4, ease: "easeOut" }}
                        className="flex-1"
                    >
                        {children}
                    </motion.div>
                </main>
            </div>
        </div>
    );
}
