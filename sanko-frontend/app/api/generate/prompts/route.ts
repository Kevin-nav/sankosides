// app/api/generate/prompts/route.ts
// Returns available prompts for the playground
import { NextResponse } from 'next/server';

// Default prompts - these could come from the backend in the future
const DEFAULT_PROMPTS = {
    CLARIFIER_SYSTEM: `You are an expert presentation architect helping users design academic presentations.
Your role is to ask clarifying questions to understand:
- The topic and scope
- Target audience and their knowledge level
- Desired number of slides
- Visual style preferences
- Key points that must be covered
- Any specific requirements or constraints

Ask questions one at a time and be conversational.`,

    BLUEPRINT_GENERATION: `Based on the gathered requirements, create a detailed slide-by-slide outline.
For each slide, specify:
- Title
- Content type (title, content, section, two_column, conclusion)
- Brief description
- Whether it needs diagrams, equations, or citations

Ensure logical flow and appropriate pacing for the target audience.`,
};

export async function GET() {
    return NextResponse.json(DEFAULT_PROMPTS);
}
