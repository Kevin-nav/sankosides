import { NextRequest, NextResponse } from "next/server";
import { adminAuth } from "@/lib/firebase-admin";
import { db, schema } from "@/lib/db";
import { eq, desc } from "drizzle-orm";

/**
 * GET /api/projects
 * Fetches all projects for the authenticated user
 */
export async function GET(request: NextRequest) {
    try {
        const authHeader = request.headers.get("Authorization");
        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
        }

        const idToken = authHeader.split("Bearer ")[1];
        const decodedToken = await adminAuth.verifyIdToken(idToken);

        // First get the user's DB ID using firebase UID
        const users = await db
            .select()
            .from(schema.users)
            .where(eq(schema.users.firebaseUid, decodedToken.uid))
            .limit(1);

        if (users.length === 0) {
            return NextResponse.json({ projects: [] }); // Or error
        }

        const userId = users[0].id;

        const projectsList = await db
            .select()
            .from(schema.projects)
            .where(eq(schema.projects.userId, userId))
            .orderBy(desc(schema.projects.updatedAt));

        return NextResponse.json({ projects: projectsList });
    } catch (error) {
        console.error("Fetch projects error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}

/**
 * POST /api/projects
 * Creates a new project draft
 */
export async function POST(request: NextRequest) {
    try {
        const authHeader = request.headers.get("Authorization");
        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
        }

        const idToken = authHeader.split("Bearer ")[1];
        const decodedToken = await adminAuth.verifyIdToken(idToken);

        const body = await request.json();
        const { title, mode } = body;

        // Get user ID
        const users = await db
            .select()
            .from(schema.users)
            .where(eq(schema.users.firebaseUid, decodedToken.uid))
            .limit(1);

        if (users.length === 0) return NextResponse.json({ error: "User not found" }, { status: 404 });

        const [newProject] = await db.insert(schema.projects).values({
            userId: users[0].id,
            title: title || "Untitled Presentation",
            mode: mode,
            status: "draft",
        }).returning();

        return NextResponse.json({ project: newProject });

    } catch (error) {
        console.error("Create project error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
