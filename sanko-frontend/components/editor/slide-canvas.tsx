"use client";

import { useMemo, useRef, useState, type MouseEvent } from "react";
import type { SlideElement, SlideElementTree } from "@/types/generation";
import { useSlideEditor } from "@/hooks/use-slide-editor";
import { TextElement } from "@/components/editor/elements/text-element";
import { ImageElement } from "@/components/editor/elements/image-element";
import { EquationElement } from "@/components/editor/elements/equation-element";
import { DiagramElement } from "@/components/editor/elements/diagram-element";

type DragState = {
    id: string;
    startX: number;
    startY: number;
    originalX: number;
    originalY: number;
    width: number;
    height: number;
} | null;

interface SlideCanvasProps {
    tree: SlideElementTree;
    editable?: boolean;
    onTreeChange?: (tree: SlideElementTree) => void;
}

function clamp(value: number, min: number, max: number): number {
    if (value < min) return min;
    if (value > max) return max;
    return value;
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

export function SlideCanvas({ tree: inputTree, editable = false, onTreeChange }: SlideCanvasProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const dragRef = useRef<DragState>(null);
    const { tree, updateElementPosition } = useSlideEditor(inputTree);
    const [activeId, setActiveId] = useState<string | null>(null);

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

    const handleMouseDown = (event: MouseEvent, element: SlideElement) => {
        if (!editable || !containerRef.current) return;
        dragRef.current = {
            id: element.id,
            startX: event.clientX,
            startY: event.clientY,
            originalX: element.x,
            originalY: element.y,
            width: element.width,
            height: element.height,
        };
        setActiveId(element.id);
    };

    const handleMouseMove = (event: MouseEvent) => {
        if (!editable || !dragRef.current || !containerRef.current) return;
        const rect = containerRef.current.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return;

        const dxPercent = ((event.clientX - dragRef.current.startX) / rect.width) * 100;
        const dyPercent = ((event.clientY - dragRef.current.startY) / rect.height) * 100;
        const maxX = Math.max(0, 100 - dragRef.current.width);
        const maxY = Math.max(0, 100 - dragRef.current.height);
        const nextX = clamp(dragRef.current.originalX + dxPercent, 0, maxX);
        const nextY = clamp(dragRef.current.originalY + dyPercent, 0, maxY);

        updateElementPosition(dragRef.current.id, nextX, nextY);
    };

    const handleMouseUp = () => {
        if (!editable) return;
        dragRef.current = null;
        setActiveId(null);
        if (onTreeChange) onTreeChange(tree);
    };

    return (
        <div
            ref={containerRef}
            className="relative h-full w-full overflow-hidden"
            style={backgroundStyle}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={handleMouseUp}
        >
            {tree.elements.map((element) => (
                <div
                    key={element.id}
                    className={`absolute ${editable ? "cursor-move select-none" : ""} ${activeId === element.id ? "ring-2 ring-emerald-400" : ""}`}
                    style={{
                        left: `${element.x}%`,
                        top: `${element.y}%`,
                        width: `${element.width}%`,
                        height: `${element.height}%`,
                        zIndex: element.z_index ?? 0,
                    }}
                    onMouseDown={(event) => handleMouseDown(event, element)}
                >
                    {renderElement(element)}
                </div>
            ))}
        </div>
    );
}
