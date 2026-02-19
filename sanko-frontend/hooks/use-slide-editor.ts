"use client";

import { useCallback, useEffect, useState } from "react";
import type { SlideElementTree } from "@/types/generation";

export function useSlideEditor(initialTree: SlideElementTree) {
    const [tree, setTree] = useState<SlideElementTree>(initialTree);

    useEffect(() => {
        setTree(initialTree);
    }, [initialTree]);

    const updateElementPosition = useCallback((id: string, x: number, y: number) => {
        setTree((prev) => ({
            ...prev,
            elements: prev.elements.map((el) => (el.id === id ? { ...el, x, y } : el)),
        }));
    }, []);

    return {
        tree,
        setTree,
        updateElementPosition,
    };
}
