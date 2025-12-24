import { NextRequest, NextResponse } from "next/server";
import { adminAuth } from "@/lib/firebase-admin";
import { db, schema } from "@/lib/db";
import { eq, and } from "drizzle-orm";

/**
 * GET /api/projects/[id]
 * Fetch a single project by ID.
 * Ensures the project belongs to the authenticated user.
 */
export async function GET(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id } = await params;

        const authHeader = request.headers.get("Authorization");
        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
        }

        const idToken = authHeader.split("Bearer ")[1];
        const decodedToken = await adminAuth.verifyIdToken(idToken);

        // Get user ID
        const users = await db
            .select()
            .from(schema.users)
            .where(eq(schema.users.firebaseUid, decodedToken.uid))
            .limit(1);

        if (users.length === 0) {
            return NextResponse.json({ error: "User not found" }, { status: 404 });
        }
        const userId = users[0].id;

        // Fetch project
        const projects = await db
            .select()
            .from(schema.projects)
            .where(and(
                eq(schema.projects.id, id),
                eq(schema.projects.userId, userId)
            ))
            .limit(1);

        if (projects.length === 0) {
            return NextResponse.json({ error: "Project not found" }, { status: 404 });
        }

        return NextResponse.json({ project: projects[0] });

    } catch (error) {
        console.error("Fetch project error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
