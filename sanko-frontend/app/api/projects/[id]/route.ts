import { NextRequest, NextResponse } from "next/server";
import { adminAuth } from "@/lib/firebase-admin";
import { db, schema } from "@/lib/db";
import { eq, and } from "drizzle-orm";

const FALLBACK_TITLE = "Untitled Presentation";
const MAX_TITLE_LENGTH = 120;
const ALLOWED_STATUSES = new Set(["draft", "negotiating", "generating", "completed", "archived"]);
const ALLOWED_RESTORE_STATUSES = new Set(["draft", "negotiating", "generating", "completed"]);

function sanitizeTitle(rawTitle: unknown): string {
    if (typeof rawTitle !== "string") return FALLBACK_TITLE;
    const normalized = rawTitle.replace(/\s+/g, " ").trim();
    if (!normalized) return FALLBACK_TITLE;
    return normalized.slice(0, MAX_TITLE_LENGTH);
}

type AuthResult = { userId: string | null; status: number; error?: string };

async function getUserIdFromAuth(request: NextRequest): Promise<AuthResult> {
    const authHeader = request.headers.get("Authorization");
    if (!authHeader || !authHeader.startsWith("Bearer ")) {
        return { userId: null, status: 401, error: "Unauthorized" };
    }

    const idToken = authHeader.split("Bearer ")[1];
    const decodedToken = await adminAuth.verifyIdToken(idToken);

    const users = await db
        .select()
        .from(schema.users)
        .where(eq(schema.users.firebaseUid, decodedToken.uid))
        .limit(1);

    if (users.length === 0) return { userId: null, status: 404, error: "User not found" };
    return { userId: users[0].id, status: 200 };
}

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
        const auth = await getUserIdFromAuth(request);
        if (!auth.userId) {
            return NextResponse.json({ error: auth.error }, { status: auth.status });
        }
        const userId = auth.userId;

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

/**
 * PATCH /api/projects/[id]
 * Update project title/status/description while enforcing ownership.
 */
export async function PATCH(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id } = await params;
        const auth = await getUserIdFromAuth(request);
        if (!auth.userId) {
            return NextResponse.json({ error: auth.error }, { status: auth.status });
        }
        const userId = auth.userId;

        const existing = await db
            .select()
            .from(schema.projects)
            .where(and(eq(schema.projects.id, id), eq(schema.projects.userId, userId)))
            .limit(1);

        if (existing.length === 0) {
            return NextResponse.json({ error: "Project not found" }, { status: 404 });
        }

        const body = await request.json();
        const updatePayload: {
            title?: string;
            description?: string;
            status?: string;
            archiveSourceStatus?: string | null;
        } = {};

        if (body.title !== undefined) {
            updatePayload.title = sanitizeTitle(body.title);
        }

        if (body.description !== undefined) {
            updatePayload.description = typeof body.description === "string" ? body.description : "";
        }

        if (body.status !== undefined) {
            if (typeof body.status !== "string" || !ALLOWED_STATUSES.has(body.status)) {
                return NextResponse.json({ error: "Invalid status" }, { status: 400 });
            }
            updatePayload.status = body.status;
        }

        if (body.archiveSourceStatus !== undefined) {
            if (
                body.archiveSourceStatus !== null &&
                (typeof body.archiveSourceStatus !== "string" || !ALLOWED_RESTORE_STATUSES.has(body.archiveSourceStatus))
            ) {
                return NextResponse.json({ error: "Invalid archiveSourceStatus" }, { status: 400 });
            }
            updatePayload.archiveSourceStatus = body.archiveSourceStatus;
        }

        if (Object.keys(updatePayload).length === 0) {
            return NextResponse.json({ error: "No valid fields provided" }, { status: 400 });
        }

        const [updated] = await db
            .update(schema.projects)
            .set({
                ...updatePayload,
                updatedAt: new Date(),
            })
            .where(and(eq(schema.projects.id, id), eq(schema.projects.userId, userId)))
            .returning();

        return NextResponse.json({ project: updated });
    } catch (error) {
        console.error("Update project error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}

/**
 * DELETE /api/projects/[id]
 * Permanently delete a project while enforcing ownership.
 */
export async function DELETE(
    request: NextRequest,
    { params }: { params: Promise<{ id: string }> }
) {
    try {
        const { id } = await params;
        const auth = await getUserIdFromAuth(request);
        if (!auth.userId) {
            return NextResponse.json({ error: auth.error }, { status: auth.status });
        }
        const userId = auth.userId;

        const deleted = await db
            .delete(schema.projects)
            .where(and(eq(schema.projects.id, id), eq(schema.projects.userId, userId)))
            .returning({ id: schema.projects.id });

        if (deleted.length === 0) {
            return NextResponse.json({ error: "Project not found" }, { status: 404 });
        }

        return NextResponse.json({ success: true });
    } catch (error) {
        console.error("Delete project error:", error);
        return NextResponse.json({ error: "Internal Server Error" }, { status: 500 });
    }
}
