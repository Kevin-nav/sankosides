// app/api/generate/processing-status/[hash]/route.ts
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ hash: string }> }
) {
    try {
        const { hash } = await params;

        const response = await fetch(`${BACKEND_URL}/api/generation/processing-status/${hash}`, {
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
        console.error('Processing status error:', error);
        return NextResponse.json(
            { detail: 'Failed to connect to backend' },
            { status: 503 }
        );
    }
}
