import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

/**
 * GET /api/universities/[universityId]/faculties
 * Proxies to backend to list faculties for a university.
 */
export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ universityId: string }> }
) {
    try {
        const { universityId } = await params;

        const response = await fetch(
            `${BACKEND_URL}/api/universities/${universityId}/faculties`,
            {
                method: "GET",
                headers: {
                    "Content-Type": "application/json",
                },
            }
        );

        if (!response.ok) {
            const error = await response.json();
            return NextResponse.json(error, { status: response.status });
        }

        const data = await response.json();
        return NextResponse.json(data);
    } catch (error) {
        console.error("Error fetching faculties:", error);
        return NextResponse.json(
            { error: "Failed to fetch faculties" },
            { status: 500 }
        );
    }
}
