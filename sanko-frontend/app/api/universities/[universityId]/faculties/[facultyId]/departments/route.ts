import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8080";

/**
 * GET /api/universities/[universityId]/faculties/[facultyId]/departments
 * Proxies to backend to list departments for a faculty.
 */
export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ universityId: string; facultyId: string }> }
) {
    try {
        const { universityId, facultyId } = await params;

        const response = await fetch(
            `${BACKEND_URL}/api/universities/${universityId}/faculties/${facultyId}/departments`,
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
        console.error("Error fetching departments:", error);
        return NextResponse.json(
            { error: "Failed to fetch departments" },
            { status: 500 }
        );
    }
}
