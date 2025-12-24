// app/api/generate/stream/[id]/route.ts
// SSE streaming route - proxies events from backend
import { NextRequest } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8080';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    const { id } = await params;

    // Create a TransformStream to forward SSE events
    const encoder = new TextEncoder();
    const stream = new TransformStream();
    const writer = stream.writable.getWriter();

    // Connect to backend SSE stream
    const backendUrl = `${BACKEND_URL}/api/generation/stream/${id}`;

    (async () => {
        try {
            const response = await fetch(backendUrl, {
                headers: {
                    'Accept': 'text/event-stream',
                    'Cache-Control': 'no-cache',
                },
            });

            if (!response.ok) {
                await writer.write(
                    encoder.encode(`event: error\ndata: {"message":"Backend connection failed"}\n\n`)
                );
                await writer.close();
                return;
            }

            const reader = response.body?.getReader();
            if (!reader) {
                await writer.close();
                return;
            }

            const decoder = new TextDecoder();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                await writer.write(encoder.encode(chunk));
            }

            await writer.close();
        } catch (error) {
            console.error('Stream error:', error);
            try {
                await writer.write(
                    encoder.encode(`event: error\ndata: {"message":"Stream connection lost"}\n\n`)
                );
                await writer.close();
            } catch {
                // Writer may already be closed
            }
        }
    })();

    return new Response(stream.readable, {
        headers: {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache, no-transform',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no',
        },
    });
}
