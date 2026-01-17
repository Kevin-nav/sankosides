// app/api/generate/start/route.ts
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json().catch(() => ({}));

        // Build URL with query parameters for session metadata
        const url = new URL(`${BACKEND_URL}/api/generation/start`);

        // Add optional parameters as query params
        if (body.project_id) {
            url.searchParams.append('project_id', body.project_id);
        }
        if (body.mode) {
            url.searchParams.append('mode', body.mode);
        }
        if (body.topic) {
            url.searchParams.append('topic', body.topic);
        }

        const response = await fetch(url.toString(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            // Backend endpoint accepts query params, not body for these fields
        });

        const data = await response.json();

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status });
        }

        return NextResponse.json(data);
    } catch (error) {
        console.error('Start session error:', error);
        return NextResponse.json(
            { detail: 'Failed to connect to backend' },
            { status: 503 }
        );
    }
}
