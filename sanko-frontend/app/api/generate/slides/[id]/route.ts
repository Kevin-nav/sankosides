// app/api/generate/slides/[id]/route.ts
/**
 * Slides API Route
 * 
 * Proxies slide requests to the backend generation result endpoint.
 * This route was missing, causing 404 errors when the frontend
 * tried to fetch generated slides.
 */
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id } = await params;

        // Fetch slides from the backend result endpoint
        const response = await fetch(`${BACKEND_URL}/api/generation/result/${id}`, {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status });
        }

        return NextResponse.json(data);
    } catch (error) {
        console.error('Slides fetch error:', error);
        return NextResponse.json(
            { detail: 'Failed to connect to backend' },
            { status: 503 }
        );
    }
}
