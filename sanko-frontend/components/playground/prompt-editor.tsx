"use client";

import { Textarea } from "@/components/ui/textarea";
import { useEffect, useState } from "react";

interface PromptEditorProps {
    value: string;
    onChange: (value: string) => void;
}

export function PromptEditor({ value, onChange }: PromptEditorProps) {
    const [localValue, setLocalValue] = useState(value);

    useEffect(() => {
        setLocalValue(value);
    }, [value]);

    return (
        <Textarea
            className="w-full bg-neutral-900 border-neutral-800 text-neutral-300 text-xs font-mono min-h-[100px] resize-y focus:ring-emerald-500/20 focus:border-emerald-500/50"
            value={localValue}
            onChange={(e) => {
                setLocalValue(e.target.value);
                onChange(e.target.value);
            }}
        />
    );
}
