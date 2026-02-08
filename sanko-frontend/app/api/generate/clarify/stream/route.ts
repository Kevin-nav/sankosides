// app/api/generate/clarify/stream/route.ts
// Streaming clarification endpoint - proxies events from backend
import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function POST(request: NextRequest) {
    try {
        const body = await request.json();
        const { session_id, answer, file_hashes } = body;

        if (!session_id) {
            return NextResponse.json(
                { detail: 'session_id is required' },
                { status: 400 }
            );
        }

        // The backend uses a non-streaming clarify endpoint
        // We'll call it and wrap the response as SSE for frontend compatibility
        const response = await fetch(`${BACKEND_URL}/api/generation/clarify/${session_id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                // Ensure message is never undefined - backend requires this field
                message: answer || 'Continue',
                file_hashes: file_hashes || undefined,
            }),
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            return NextResponse.json(error, { status: response.status });
        }

        const data = await response.json();

        // Convert response to SSE format for frontend compatibility
        const encoder = new TextEncoder();
        const stream = new ReadableStream({
            start(controller) {
                // Determine content to display
                // Priority: question (agent text) > message (system text) > default
                const content = data.question || data.message || 'Got it! Let me process that...';

                // Send content event with the response
                controller.enqueue(
                    encoder.encode(`event: content\ndata: ${JSON.stringify({ text: content })}\n\n`)
                );

                // Handle Confirmation requirement
                if (data.needs_confirmation) {
                    controller.enqueue(
                        encoder.encode(`event: needs_confirmation\ndata: ${JSON.stringify({
                            summary: data.summary,
                            message: data.message
                        })}\n\n`)
                    );
                }

                // Send done event
                controller.enqueue(
                    encoder.encode(`event: done\ndata: ${JSON.stringify({
                        content: content,
                        complete: data.complete,
                        order_form: data.order_form,
                    })}\n\n`)
                );

                // If clarification is complete, signal blueprint_ready
                if (data.complete && data.order_form) {
                    controller.enqueue(
                        encoder.encode(`event: blueprint_ready\ndata: ${JSON.stringify({
                            session_id: data.session_id,
                            order_form: data.order_form,
                        })}\n\n`)
                    );
                }

                controller.close();
            },
        });

        return new Response(stream, {
            headers: {
                'Content-Type': 'text/event-stream',
                'Cache-Control': 'no-cache, no-transform',
                'Connection': 'keep-alive',
            },
        });
    } catch (error) {
        console.error('Clarify stream error:', error);
        return NextResponse.json(
            { detail: 'Failed to connect to backend' },
            { status: 503 }
        );
    }
}
