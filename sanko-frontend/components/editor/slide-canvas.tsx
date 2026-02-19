"use client";

import { useMemo } from "react";
import type { SlideElement, SlideElementTree } from "@/types/generation";
import { TextElement } from "@/components/editor/elements/text-element";
import { ImageElement } from "@/components/editor/elements/image-element";
import { EquationElement } from "@/components/editor/elements/equation-element";
import { DiagramElement } from "@/components/editor/elements/diagram-element";

interface SlideCanvasProps {
    tree: SlideElementTree;
}

function renderElement(element: SlideElement) {
    switch (element.type) {
        case "text":
            return <TextElement element={element} />;
        case "image":
            return <ImageElement element={element} />;
        case "equation":
            return <EquationElement element={element} />;
        case "diagram":
            return <DiagramElement element={element} />;
        default:
            return <div className="h-full w-full rounded border border-dashed border-neutral-300" />;
    }
}

export function SlideCanvas({ tree }: SlideCanvasProps) {
    const backgroundStyle = useMemo(() => {
        const bg = tree.background ?? {};
        if (bg.type === "gradient" && typeof bg.gradient === "string") {
            return { background: bg.gradient };
        }
        if (bg.type === "image" && typeof bg.image_url === "string" && bg.image_url) {
            return {
                backgroundImage: `url(${bg.image_url})`,
                backgroundSize: "cover",
                backgroundPosition: "center",
            };
        }
        return { background: typeof bg.color === "string" ? bg.color : "#ffffff" };
    }, [tree.background]);

    return (
        <div
            className="relative h-full w-full overflow-hidden"
            style={backgroundStyle}
        >
            {tree.elements.map((element) => (
                <div
                    key={element.id}
                    className="absolute"
                    style={{
                        left: `${element.x}%`,
                        top: `${element.y}%`,
                        width: `${element.width}%`,
                        height: `${element.height}%`,
                        zIndex: element.z_index ?? 0,
                    }}
                >
                    {renderElement(element)}
                </div>
            ))}
        </div>
    );
}
