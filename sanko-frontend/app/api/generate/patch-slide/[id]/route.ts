// app/api/generate/patch-slide/[id]/route.ts
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id } = await params;
        const body = await request.json().catch(() => ({}));

        const response = await fetch(`${BACKEND_URL}/api/generation/patch-slide/${id}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) return NextResponse.json(data, { status: response.status });
        return NextResponse.json(data);
    } catch (error) {
        console.error("Patch slide error:", error);
        return NextResponse.json({ detail: "Failed to connect to backend" }, { status: 503 });
    }
}

