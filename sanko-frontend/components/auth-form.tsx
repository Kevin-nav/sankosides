"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Eye, EyeOff, X, AlertCircle } from "lucide-react";

interface AuthFormProps {
    mode: "login" | "register";
}

// Official Google Icon SVG
function GoogleIcon({ className }: { className?: string }) {
    return (
        <svg className={className} viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <g fill="none" fillRule="evenodd">
                <path d="M12.24 10.285V14.4h6.806c-.275 1.765-2.056 5.174-6.806 5.174-4.095 0-7.439-3.389-7.439-7.574s3.345-7.574 7.439-7.574c2.33 0 3.891.989 4.785 1.849l3.254-3.138C18.189 1.186 15.479 0 12.24 0c-6.635 0-12 5.365-12 12s5.365 12 12 12c6.926 0 11.52-4.869 11.52-11.726 0-.788-.085-1.39-.189-1.989H12.24z" fill="currentColor" />
            </g>
        </svg>
    );
}

export function AuthForm({ mode }: AuthFormProps) {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [agreedToTerms, setAgreedToTerms] = useState(false);

    const router = useRouter();
    const { loginWithGoogle, loginWithEmail, registerWithEmail } = useAuth();

    const calculateStrength = (pass: string) => {
        let score = 0;
        if (!pass) return 0;
        if (pass.length > 6) score++;
        if (pass.length > 10) score++;
        if (/[A-Z]/.test(pass)) score++;
        if (/[0-9]/.test(pass)) score++;
        if (/[^A-Za-z0-9]/.test(pass)) score++;
        return score > 4 ? 4 : score; // Cap at 4 (bars)
    };

    const strength = calculateStrength(password);
    const strengthColor = ["bg-neutral-800", "bg-red-500", "bg-orange-500", "bg-yellow-500", "bg-emerald-500"];

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);
        setIsLoading(true);

        if (mode === "register" && !agreedToTerms) {
            setError("You must agree to the Terms of Service.");
            setIsLoading(false);
            return;
        }

        try {
            if (mode === "login") {
                await loginWithEmail(email, password);
            } else {
                await registerWithEmail(email, password);
            }
            router.push("/dashboard");
        } catch (err: any) {
            setError(err.message || "An error occurred");
        } finally {
            setIsLoading(false);
        }
    };

    const handleGoogleAuth = async () => {
        setError(null);
        setIsLoading(true);
        try {
            await loginWithGoogle();
            router.push("/dashboard");
        } catch (err: any) {
            if (err.code === 'auth/popup-closed-by-user') {
                setError(null);
            } else {
                setError(err.message || "Google sign-in failed");
            }
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="w-full max-w-[400px] space-y-6">
            <div className="space-y-2 text-center">
                <h1 className="text-3xl font-bold tracking-tight text-white">
                    {mode === "login" ? "Welcome back" : "Create an account"}
                </h1>
                <p className="text-sm text-neutral-400">
                    {mode === "login"
                        ? "Enter your credentials to access your workspace"
                        : "Enter your email below to create your account"}
                </p>
            </div>

            <div className="space-y-4">
                <Button
                    variant="outline"
                    className="w-full bg-neutral-900 border-neutral-800 text-neutral-300 hover:bg-neutral-800 hover:text-white h-11 font-medium"
                    onClick={handleGoogleAuth}
                    disabled={isLoading}
                >
                    {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <GoogleIcon className="mr-2 h-4 w-4" />}
                    Continue with Google
                </Button>

                <div className="relative">
                    <div className="absolute inset-0 flex items-center">
                        <span className="w-full border-t border-neutral-800" />
                    </div>
                    <div className="relative flex justify-center text-xs uppercase">
                        <span className="bg-neutral-950 px-2 text-neutral-500">Or continue with</span>
                    </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div className="space-y-2">
                        <Label htmlFor="email" className="text-neutral-300">Email</Label>
                        <Input
                            id="email"
                            type="email"
                            placeholder="m@example.com"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            required
                            className="bg-neutral-900 border-neutral-800 text-white placeholder:text-neutral-600 focus-visible:ring-emerald-500/50 h-11 invalid:border-red-500/50 focus:invalid:ring-red-500/50"
                            disabled={isLoading}
                        />
                    </div>
                    <div className="space-y-2">
                        <div className="flex items-center justify-between">
                            <Label htmlFor="password" className="text-neutral-300">Password</Label>
                            {mode === "login" && (
                                <a href="#" className="text-xs text-emerald-500 hover:text-emerald-400">Forgot password?</a>
                            )}
                        </div>
                        <div className="relative">
                            <Input
                                id="password"
                                type={showPassword ? "text" : "password"}
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                className="bg-neutral-900 border-neutral-800 text-white focus-visible:ring-emerald-500/50 h-11 pr-10"
                                disabled={isLoading}
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-500 hover:text-white transition-colors"
                            >
                                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                            </button>
                        </div>

                        {/* Password Strength Meter (Only on Register) */}
                        {mode === "register" && password && (
                            <div className="space-y-1 pt-1">
                                <div className="flex gap-1 h-1">
                                    {[1, 2, 3, 4].map((level) => (
                                        <div
                                            key={level}
                                            className={`flex-1 rounded-full transition-colors duration-300 ${strength >= level ? strengthColor[strength] : "bg-neutral-800"}`}
                                        />
                                    ))}
                                </div>
                                <p className="text-[10px] text-neutral-500 text-right">
                                    {strength === 0 && "Too weak"}
                                    {strength === 1 && "Weak"}
                                    {strength === 2 && "Fair"}
                                    {strength === 3 && "Good"}
                                    {strength === 4 && "Strong"}
                                </p>
                            </div>
                        )}
                    </div>

                    {error && (
                        <div className="bg-red-500/10 border border-red-500/20 rounded-md p-3 text-sm text-red-400 flex items-start gap-2">
                            <div className="flex-1 flex items-center gap-2">
                                <AlertCircle className="h-4 w-4" />
                                <span>{error}</span>
                            </div>
                            <button onClick={() => setError(null)} className="text-red-400 hover:text-red-300 transition-colors">
                                <X className="h-4 w-4" />
                                <span className="sr-only">Close</span>
                            </button>
                        </div>
                    )}

                    {/* Terms Agreement (Register only) */}
                    {mode === "register" && (
                        <div className="flex items-start space-x-2">
                            <div className="flex h-5 items-center">
                                <input
                                    id="terms"
                                    type="checkbox"
                                    checked={agreedToTerms}
                                    onChange={(e) => setAgreedToTerms(e.target.checked)}
                                    className="h-4 w-4 rounded border-neutral-700 bg-neutral-900 text-emerald-600 focus:ring-emerald-500/50 focus:ring-offset-0 disabled:cursor-not-allowed disabled:opacity-50"
                                />
                            </div>
                            <Label htmlFor="terms" className="text-sm text-neutral-400 font-normal leading-tight cursor-pointer">
                                I agree to the <Link href="/terms" className="text-emerald-500 hover:underline">Terms of Service</Link> and <Link href="/privacy" className="text-emerald-500 hover:underline">Privacy Policy</Link>.
                            </Label>
                        </div>
                    )}

                    <Button type="submit" className="w-full bg-emerald-600 hover:bg-emerald-500 text-white h-11 font-medium" disabled={isLoading || (mode === "register" && !agreedToTerms)}>
                        {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        {mode === "login" ? "Sign In" : "Create Account"}
                    </Button>
                </form>

                <div className="text-center text-sm text-neutral-400">
                    {mode === "login" ? "Don't have an account? " : "Already have an account? "}
                    <a href={mode === "login" ? "/register" : "/login"} className="text-emerald-500 hover:underline hover:text-emerald-400 font-medium">
                        {mode === "login" ? "Sign up" : "Sign in"}
                    </a>
                </div>
            </div>
        </div>
    );
}
