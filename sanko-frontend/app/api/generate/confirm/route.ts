// app/api/generate/confirm/route.ts
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json().catch(() => ({}));
        const sessionId = body.session_id;

        if (!sessionId) {
            return NextResponse.json(
                { detail: 'session_id is required' },
                { status: 400 }
            );
        }

        const response = await fetch(`${BACKEND_URL}/api/generation/confirm/${sessionId}`, {
            method: 'POST',
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
        console.error('Confirm error:', error);
        return NextResponse.json(
            { detail: 'Failed to connect to backend' },
            { status: 503 }
        );
    }
}
