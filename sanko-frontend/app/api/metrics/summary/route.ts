// app/api/metrics/summary/route.ts
// Returns aggregate metrics (placeholder until session-specific metrics are used)
import { NextResponse } from 'next/server';

export async function GET() {
    // Return placeholder metrics until a session is active
    // The playground component handles this gracefully with fallback
    return NextResponse.json({
        total_agents: 0,
        successful_agents: 0,
        failed_agents: 0,
        total_tokens: 0,
        total_input_tokens: 0,
        total_output_tokens: 0,
        total_thinking_tokens: 0,
        total_duration_ms: 0,
        total_cost_usd: 0,
        agents: {},
    });
}
