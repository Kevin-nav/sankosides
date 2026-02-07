"use client";

import { ReactNode } from "react";
import { ConvexProvider, ConvexReactClient } from "convex/react";

const convexUrl = process.env.NEXT_PUBLIC_CONVEX_URL || "https://placeholder.convex.cloud";

const convex = new ConvexReactClient(convexUrl);

export function ConvexClientProvider({ children }: { children: ReactNode }) {
    // Safe guard: only render provider if URL is real or we want to allow failure?
    // Usually we just render it. The client might log errors if URL is invalid.
    return <ConvexProvider client={convex}>{children}</ConvexProvider>;
}
