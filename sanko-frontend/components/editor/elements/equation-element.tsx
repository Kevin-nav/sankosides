"use client";

import type { SlideElement } from "@/types/generation";

type EquationContent = {
    latex?: string;
    rendered_svg?: string;
};

function getEquationContent(element: SlideElement): EquationContent {
    return (element.content as EquationContent | undefined) ?? {};
}

export function EquationElement({ element }: { element: SlideElement }) {
    const content = getEquationContent(element);

    if (content.rendered_svg) {
        return (
            <div
                className="flex h-full w-full items-center justify-center"
                dangerouslySetInnerHTML={{ __html: content.rendered_svg }}
            />
        );
    }

    return (
        <div className="flex h-full w-full items-center justify-center rounded border border-neutral-200 bg-neutral-50 px-2 text-center text-xs text-neutral-700">
            <code>{content.latex ?? "Equation unavailable"}</code>
        </div>
    );
}
