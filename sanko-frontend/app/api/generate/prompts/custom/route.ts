// app/api/generate/prompts/custom/route.ts
// Returns user's custom prompt overrides (placeholder)
import { NextResponse } from 'next/server';

// GET custom prompt overrides
export async function GET() {
    // Return empty object - no custom overrides by default
    // In the future, this could read from user preferences or localStorage
    return NextResponse.json({});
}

// POST to save custom prompt overrides
export async function POST(request: Request) {
    try {
        const body = await request.json();
        // In the future, this could save to database
        // For now, just acknowledge the save
        return NextResponse.json({
            success: true,
            message: 'Custom prompts saved',
            prompts: body
        });
    } catch (error) {
        return NextResponse.json(
            { error: 'Failed to save prompts' },
            { status: 400 }
        );
    }
}
