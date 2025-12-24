"use client";

import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { signOut } from "firebase/auth";
import { auth } from "@/lib/firebase";
import { Sparkles, Menu, X } from "lucide-react";
import { usePathname } from "next/navigation";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { useState } from "react";

const navLinks = [
    { href: "/pricing", label: "Pricing" },
    { href: "/about", label: "About" },
    { href: "/contact", label: "Contact" },
];

export function Navbar() {
    const { user, loading } = useAuth();
    const pathname = usePathname();
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    // Determine context
    const isDashboard = pathname?.startsWith("/dashboard");
    const isAuthPage = pathname === "/login" || pathname === "/register";

    // On dashboard, show minimal navbar (logo only) for consistency
    // The DashboardShell handles the actual navigation
    if (isDashboard) {
        return null; // DashboardShell has its own header
    }

    return (
        <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-neutral-950/60 backdrop-blur-xl supports-[backdrop-filter]:bg-neutral-950/40">
            <div className="container flex h-16 items-center justify-between px-4 md:px-6">
                {/* Logo */}
                <Link href="/" className="flex items-center space-x-2 group">
                    <div className="h-8 w-8 rounded-lg bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30 group-hover:bg-emerald-500/30 transition-colors">
                        <Sparkles className="h-4 w-4 text-emerald-400" />
                    </div>
                    <span className="font-bold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white to-neutral-400">
                        SankoSlides
                    </span>
                </Link>

                {/* Auth Pages: Minimal nav - just the logo on left */}
                {isAuthPage ? (
                    <div className="flex items-center gap-4">
                        {/* Nothing on right for auth pages - keep it clean */}
                    </div>
                ) : (
                    <>
                        {/* Desktop Navigation */}
                        <div className="hidden md:flex items-center space-x-8">
                            {/* Nav Links */}
                            <div className="flex items-center space-x-6 text-sm font-medium">
                                {navLinks.map((link) => (
                                    <Link
                                        key={link.href}
                                        href={link.href}
                                        className={`transition-colors ${pathname === link.href
                                                ? "text-emerald-400"
                                                : "text-neutral-400 hover:text-white"
                                            }`}
                                    >
                                        {link.label}
                                    </Link>
                                ))}
                            </div>

                            {/* Auth Actions */}
                            {!loading && (
                                <>
                                    {user ? (
                                        <div className="flex items-center space-x-4">
                                            <span className="text-sm text-neutral-400 hidden lg:inline-block">
                                                {user.email}
                                            </span>
                                            <Button
                                                variant="ghost"
                                                className="text-neutral-400 hover:text-white"
                                                onClick={() => signOut(auth)}
                                            >
                                                Log out
                                            </Button>
                                            <Button
                                                size="sm"
                                                className="bg-emerald-600 hover:bg-emerald-500 text-white"
                                                asChild
                                            >
                                                <Link href="/dashboard">Dashboard</Link>
                                            </Button>
                                        </div>
                                    ) : (
                                        <div className="flex items-center gap-4">
                                            <Link
                                                href="/login"
                                                className="text-neutral-400 hover:text-white transition-colors"
                                            >
                                                Sign in
                                            </Link>
                                            <Button
                                                size="sm"
                                                className="bg-emerald-600 hover:bg-emerald-500 text-white shadow-[0_0_15px_-3px_rgba(16,185,129,0.4)] hover:shadow-[0_0_20px_-3px_rgba(16,185,129,0.6)] transition-all"
                                                asChild
                                            >
                                                <Link href="/register">Get Started</Link>
                                            </Button>
                                        </div>
                                    )}
                                </>
                            )}
                        </div>

                        {/* Mobile Navigation */}
                        <div className="md:hidden flex items-center gap-2">
                            {/* Quick auth buttons on mobile */}
                            {!loading && !user && (
                                <Button
                                    size="sm"
                                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3"
                                    asChild
                                >
                                    <Link href="/register">Get Started</Link>
                                </Button>
                            )}
                            {!loading && user && (
                                <Button
                                    size="sm"
                                    className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-3"
                                    asChild
                                >
                                    <Link href="/dashboard">Dashboard</Link>
                                </Button>
                            )}

                            {/* Hamburger Menu */}
                            <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
                                <SheetTrigger asChild>
                                    <Button
                                        variant="ghost"
                                        size="icon"
                                        className="text-neutral-400 hover:text-white"
                                    >
                                        <Menu className="h-5 w-5" />
                                        <span className="sr-only">Menu</span>
                                    </Button>
                                </SheetTrigger>
                                <SheetContent
                                    side="right"
                                    className="w-[300px] bg-neutral-950 border-l border-neutral-800 text-white"
                                >
                                    <div className="flex flex-col h-full">
                                        {/* Logo in Sheet */}
                                        <div className="flex items-center space-x-2 mb-8">
                                            <div className="h-8 w-8 rounded-lg bg-emerald-500/20 flex items-center justify-center border border-emerald-500/30">
                                                <Sparkles className="h-4 w-4 text-emerald-400" />
                                            </div>
                                            <span className="font-bold text-lg tracking-tight text-white">
                                                SankoSlides
                                            </span>
                                        </div>

                                        {/* Nav Links */}
                                        <nav className="flex flex-col space-y-4">
                                            {navLinks.map((link) => (
                                                <Link
                                                    key={link.href}
                                                    href={link.href}
                                                    onClick={() => setMobileMenuOpen(false)}
                                                    className={`text-lg font-medium py-2 border-b border-neutral-800 transition-colors ${pathname === link.href
                                                            ? "text-emerald-400"
                                                            : "text-neutral-300 hover:text-white"
                                                        }`}
                                                >
                                                    {link.label}
                                                </Link>
                                            ))}
                                        </nav>

                                        {/* Auth Section at Bottom */}
                                        <div className="mt-auto pt-8 border-t border-neutral-800 space-y-4">
                                            {!loading && (
                                                <>
                                                    {user ? (
                                                        <>
                                                            <p className="text-sm text-neutral-400 truncate">
                                                                {user.email}
                                                            </p>
                                                            <Button
                                                                variant="outline"
                                                                className="w-full border-neutral-700 text-neutral-300 hover:bg-neutral-800 hover:text-white"
                                                                onClick={() => {
                                                                    signOut(auth);
                                                                    setMobileMenuOpen(false);
                                                                }}
                                                            >
                                                                Log out
                                                            </Button>
                                                        </>
                                                    ) : (
                                                        <>
                                                            <Button
                                                                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white"
                                                                asChild
                                                            >
                                                                <Link
                                                                    href="/register"
                                                                    onClick={() => setMobileMenuOpen(false)}
                                                                >
                                                                    Get Started
                                                                </Link>
                                                            </Button>
                                                            <Button
                                                                variant="outline"
                                                                className="w-full border-neutral-700 text-neutral-300 hover:bg-neutral-800 hover:text-white"
                                                                asChild
                                                            >
                                                                <Link
                                                                    href="/login"
                                                                    onClick={() => setMobileMenuOpen(false)}
                                                                >
                                                                    Sign in
                                                                </Link>
                                                            </Button>
                                                        </>
                                                    )}
                                                </>
                                            )}
                                        </div>
                                    </div>
                                </SheetContent>
                            </Sheet>
                        </div>
                    </>
                )}
            </div>
        </nav>
    );
}
