"use client";

import DOMPurify from "dompurify";
import type { SlideElement } from "@/types/generation";

type DiagramContent = {
    rendered_svg?: string;
    mermaid_source?: string;
};

function getDiagramContent(element: SlideElement): DiagramContent {
    return (element.content as DiagramContent | undefined) ?? {};
}

export function DiagramElement({ element }: { element: SlideElement }) {
    const content = getDiagramContent(element);
    const sanitizedSvg = content.rendered_svg
        ? DOMPurify.sanitize(content.rendered_svg, {
            USE_PROFILES: { svg: true, svgFilters: true },
            FORBID_TAGS: ["foreignObject"],
        })
        : "";

    if (sanitizedSvg) {
        return (
            <div
                className="h-full w-full"
                dangerouslySetInnerHTML={{ __html: sanitizedSvg }}
            />
        );
    }

    return (
        <pre className="h-full w-full overflow-auto rounded border border-neutral-200 bg-neutral-50 p-2 text-[10px] text-neutral-700">
            {content.mermaid_source ?? "Diagram unavailable"}
        </pre>
    );
}
