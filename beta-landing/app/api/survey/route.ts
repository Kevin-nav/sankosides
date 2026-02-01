
import { db } from '@/db';
import { surveyResponses } from '@/db/schema';
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
    try {
        const body = await request.json();

        // Basic validation
        if (!body.email) {
            return NextResponse.json(
                { error: 'Email is required' },
                { status: 400 }
            );
        }

        const newResponse = await db.insert(surveyResponses).values({
            email: body.email,
            operatingSystem: body.operatingSystem,
            browser: body.browser,
            citationStyle: body.citationStyle,
            contentSource: body.contentSource,
            visualStyle: body.visualStyle,
        }).returning();

        // Calculate a "Priority Position" (just a fun fake number for now based on total responses)
        // In a real app we'd query count. For now, random-ish but deterministic-feeling.
        const position = Math.floor(Math.random() * 500) + 100;

        return NextResponse.json({
            success: true,
            data: newResponse[0],
            priorityPosition: position
        });

    } catch (error) {
        console.error('Error submitting survey:', error);
        return NextResponse.json(
            { error: 'Failed to submit survey' },
            { status: 500 }
        );
    }
}
