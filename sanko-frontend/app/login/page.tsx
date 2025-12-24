"use client";

import Link from "next/link";
import Image from "next/image";
import { AuthForm } from "@/components/auth-form";
import { ArrowLeft, Loader2 } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LoginPage() {
    const { user, loading } = useAuth();
    const router = useRouter();

    // Redirect authenticated users to dashboard
    useEffect(() => {
        if (!loading && user) {
            router.replace("/dashboard");
        }
    }, [user, loading, router]);

    // If user is already authenticated, show loading while redirecting
    if (!loading && user) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-neutral-950">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
            </div>
        );
    }

    return (
        <div className="min-h-screen lg:h-screen lg:overflow-hidden grid lg:grid-cols-2 bg-neutral-950">
            {/* Left Column - Visual Branding */}
            <div className="relative hidden lg:flex flex-col justify-end p-12 bg-neutral-900 overflow-hidden">
                {/* Background Image / Pattern */}
                <div className="absolute inset-0 z-0">
                    <Image
                        src="/images/hero.png"
                        alt="SankoSlides Visual"
                        fill
                        className="object-cover opacity-30 mix-blend-overlay"
                        priority
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-neutral-950 via-neutral-950/50 to-transparent" />
                </div>

                <div className="relative z-10 space-y-6">
                    <div className="space-y-2">
                        <h2 className="text-3xl font-bold text-white tracking-tight">
                            The bridge between raw ideas and{" "}
                            <span className="text-emerald-500">academic excellence.</span>
                        </h2>
                        <p className="text-neutral-400 text-lg leading-relaxed">
                            We handle the layout, citations, and structure. You bring the brilliance.
                        </p>
                    </div>
                </div>
            </div>

            {/* Right Column - Form */}
            <div className="flex flex-col h-full w-full overflow-y-auto pt-24 pb-8 px-8 sm:px-12 lg:px-12">
                <div className="flex justify-end w-full mb-4 lg:mb-8">
                    <Link
                        href="/"
                        className="inline-flex items-center text-sm text-neutral-400 hover:text-white transition-colors"
                    >
                        <ArrowLeft className="mr-2 h-4 w-4" /> Back to site
                    </Link>
                </div>

                <div className="flex-1 flex flex-col items-center justify-center w-full min-h-[400px]">
                    {loading ? (
                        <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
                    ) : (
                        <div className="w-full max-w-md space-y-8 pb-12">
                            <AuthForm mode="login" />
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
