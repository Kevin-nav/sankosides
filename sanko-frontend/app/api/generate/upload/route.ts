// app/api/generate/upload/route.ts
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

export async function POST(request: NextRequest) {
    try {
        // Get the form data from the request
        const formData = await request.formData();

        // Check if files are present
        const files = formData.getAll('files');
        if (!files || files.length === 0) {
            return NextResponse.json(
                { detail: 'No files provided' },
                { status: 400 }
            );
        }

        // Forward the multipart form data to the backend
        const response = await fetch(`${BACKEND_URL}/api/generation/upload`, {
            method: 'POST',
            body: formData,
        });

        const data = await response.json();

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status });
        }

        return NextResponse.json(data);
    } catch (error) {
        console.error('Upload error:', error);
        return NextResponse.json(
            { detail: 'Failed to upload files' },
            { status: 503 }
        );
    }
}

// Route segment config for App Router
// Note: Body size limit must be configured in next.config.js via
// experimental.serverActions.bodySizeLimit if needed for larger files
export const maxDuration = 60; // Allow up to 60 seconds for file uploads
