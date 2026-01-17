import { NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

/**
 * GET /api/universities/hierarchy
 * 
 * Fetches the complete university hierarchy in ONE call.
 * Returns all universities with nested faculties and departments.
 * Backend caches this data for 1 hour.
 */
export async function GET() {
    try {
        const response = await fetch(`${BACKEND_URL}/api/universities/hierarchy`, {
            method: "GET",
            headers: {
                "Content-Type": "application/json",
            },
            // Cache on the edge for 5 minutes
            next: { revalidate: 300 },
        });

        if (!response.ok) {
            const error = await response.json();
            return NextResponse.json(error, { status: response.status });
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error("Error fetching university hierarchy:", error);
        return NextResponse.json(
            { error: "Failed to fetch university hierarchy" },
            { status: 500 }
        );
    }
}
