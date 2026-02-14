// app/api/generate/document-sections/route.ts
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

export async function POST(request: NextRequest) {
    try {
        const body = await request.json().catch(() => ({}));
        const file_hashes = Array.isArray(body.file_hashes) ? body.file_hashes : [];

        const response = await fetch(`${BACKEND_URL}/api/generation/document-sections`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ file_hashes }),
        });

        const data = await response.json().catch(() => ({}));
        if (!response.ok) return NextResponse.json(data, { status: response.status });

        return NextResponse.json(data);
    } catch (error) {
        console.error("Document sections error:", error);
        return NextResponse.json({ detail: "Failed to connect to backend" }, { status: 503 });
    }
}

