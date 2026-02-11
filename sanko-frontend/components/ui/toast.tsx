"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import { cn } from "@/lib/utils";

type ToastVariant = "success" | "error" | "info";

interface ToastItem {
    id: string;
    title: string;
    description?: string;
    variant: ToastVariant;
    durationMs: number;
}

interface ToastInput {
    title: string;
    description?: string;
    variant?: ToastVariant;
    durationMs?: number;
}

interface ToastContextValue {
    toast: (input: ToastInput) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
    const [toasts, setToasts] = useState<ToastItem[]>([]);

    const removeToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((item) => item.id !== id));
    }, []);

    const toast = useCallback((input: ToastInput) => {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
        const durationMs = input.durationMs ?? 3500;
        const item: ToastItem = {
            id,
            title: input.title,
            description: input.description,
            variant: input.variant ?? "info",
            durationMs,
        };

        setToasts((prev) => [...prev, item]);
        window.setTimeout(() => removeToast(id), durationMs);
    }, [removeToast]);

    const value = useMemo(() => ({ toast }), [toast]);

    return (
        <ToastContext.Provider value={value}>
            {children}
            <div className="pointer-events-none fixed right-3 top-16 z-[100] flex w-[min(92vw,380px)] flex-col gap-2 md:right-6 md:top-20">
                {toasts.map((item) => (
                    <div
                        key={item.id}
                        className={cn(
                            "pointer-events-auto rounded-lg border px-4 py-3 shadow-xl backdrop-blur",
                            item.variant === "success" && "border-emerald-500/30 bg-emerald-950/80 text-emerald-100",
                            item.variant === "error" && "border-red-500/30 bg-red-950/80 text-red-100",
                            item.variant === "info" && "border-neutral-700 bg-neutral-900/95 text-neutral-100",
                        )}
                    >
                        <div className="text-sm font-semibold">{item.title}</div>
                        {item.description && (
                            <div className="mt-1 text-xs text-neutral-300">{item.description}</div>
                        )}
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    );
}

export function useToast() {
    const context = useContext(ToastContext);
    if (!context) {
        throw new Error("useToast must be used within ToastProvider");
    }
    return context;
}

