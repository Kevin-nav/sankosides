"use client";

import { Separator as PanelResizeHandle } from "react-resizable-panels";
import { cn } from "@/lib/utils";

interface ResizeHandleProps {
    className?: string;
    id?: string;
}

export function ResizeHandle({ className, id }: ResizeHandleProps) {
    return (
        <PanelResizeHandle
            id={id}
            className={cn(
                "relative flex items-center justify-center w-[2px] bg-transparent transition-all z-50",
                "hover:w-[12px] group focus:outline-none focus:ring-1 focus:ring-emerald-500/50",
                "data-[resize-handle-active]:bg-emerald-500/10",
                className
            )}
        >
            <div className={cn(
                "h-full w-[1px] bg-white/10 transition-all duration-300",
                "group-hover:bg-emerald-500 group-hover:w-[2px] group-hover:shadow-[0_0_10px_rgba(16,185,129,0.5)]",
                "group-active:bg-emerald-400 group-active:w-[2px]"
            )} />

            {/* Decorative Handle Indicator */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-8 w-1 rounded-full bg-white/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
        </PanelResizeHandle>
    );
}
