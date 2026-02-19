"use client";

import type { SlideElement } from "@/types/generation";

type ImageContent = {
    url?: string;
    alt?: string;
    caption?: string;
};

function getImageContent(element: SlideElement): ImageContent {
    return (element.content as ImageContent | undefined) ?? {};
}

export function ImageElement({ element }: { element: SlideElement }) {
    const content = getImageContent(element);

    return (
        <div className="h-full w-full overflow-hidden">
            {content.url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                    src={content.url}
                    alt={content.alt ?? ""}
                    className="h-full w-full object-contain"
                    draggable={false}
                />
            ) : (
                <div className="flex h-full w-full items-center justify-center rounded border border-dashed border-neutral-300 text-xs text-neutral-500">
                    Missing image
                </div>
            )}
            {content.caption ? (
                <div className="mt-1 text-[10px] text-neutral-600">{content.caption}</div>
            ) : null}
        </div>
    );
}
