"use client";

import type { SlideElement } from "@/types/generation";

type TextRun = {
    text?: string;
    bold?: boolean;
    italic?: boolean;
    size?: number;
    color?: string;
    font?: string;
};

function getRuns(element: SlideElement): TextRun[] {
    const raw = (element.content as { runs?: unknown } | undefined)?.runs;
    return Array.isArray(raw) ? (raw as TextRun[]) : [];
}

export function TextElement({ element }: { element: SlideElement }) {
    const runs = getRuns(element);

    if (!runs.length) {
        return <div className="h-full w-full whitespace-pre-wrap text-sm text-neutral-800" />;
    }

    return (
        <div className="h-full w-full whitespace-pre-wrap leading-tight text-neutral-900">
            {runs.map((run, idx) => (
                <span
                    key={`${element.id}-run-${idx}`}
                    style={{
                        fontWeight: run.bold ? 700 : 400,
                        fontStyle: run.italic ? "italic" : "normal",
                        fontSize: run.size ? `${run.size}px` : undefined,
                        color: run.color,
                        fontFamily: run.font,
                    }}
                >
                    {run.text ?? ""}
                </span>
            ))}
        </div>
    );
}
