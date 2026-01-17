import { NextRequest, NextResponse } from "next/server";
import { adminAuth } from "@/lib/firebase-admin";
import { db, schema } from "@/lib/db";
import { eq } from "drizzle-orm";

/**
 * GET /api/user/profile
 * Fetches the current user's profile from the database.
 */
export async function GET(request: NextRequest) {
    try {
        const authHeader = request.headers.get("Authorization");
        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return NextResponse.json(
                { error: "Unauthorized" },
                { status: 401 }
            );
        }

        const idToken = authHeader.split("Bearer ")[1];
        const decodedToken = await adminAuth.verifyIdToken(idToken);

        const users = await db
            .select()
            .from(schema.users)
            .where(eq(schema.users.firebaseUid, decodedToken.uid))
            .limit(1);

        if (users.length === 0) {
            return NextResponse.json(
                { error: "User not found" },
                { status: 404 }
            );
        }

        return NextResponse.json({ user: users[0] });
    } catch (error) {
        console.error("Get profile error:", error);
        return NextResponse.json(
            { error: "Unauthorized" },
            { status: 401 }
        );
    }
}

/**
 * PUT /api/user/profile
 * Updates the current user's university profile settings.
 * 
 * Supports both legacy JSONB universityProfile AND new structured fields:
 * - universityId, facultyId, departmentId, academicLevel, academicYear, programmeId
 */
export async function PUT(request: NextRequest) {
    try {
        const authHeader = request.headers.get("Authorization");
        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return NextResponse.json(
                { error: "Unauthorized" },
                { status: 401 }
            );
        }

        const idToken = authHeader.split("Bearer ")[1];
        const decodedToken = await adminAuth.verifyIdToken(idToken);

        const body = await request.json();
        const {
            universityProfile,
            displayName,
            // New structured fields
            universityId,
            facultyId,
            departmentId,
            academicLevel,
            academicYear,
            programmeId,
        } = body;

        // Build update object with only provided fields
        const updateData: Record<string, unknown> = {
            updatedAt: new Date(),
        };

        // Legacy JSONB field
        if (universityProfile !== undefined) {
            updateData.universityProfile = universityProfile;
        }
        if (displayName !== undefined) {
            updateData.displayName = displayName;
        }

        // New structured fields
        if (universityId !== undefined) {
            updateData.universityId = universityId;
        }
        if (facultyId !== undefined) {
            updateData.facultyId = facultyId;
        }
        if (departmentId !== undefined) {
            updateData.departmentId = departmentId;
        }
        if (academicLevel !== undefined) {
            updateData.academicLevel = academicLevel;
        }
        if (academicYear !== undefined) {
            updateData.academicYear = academicYear;
        }
        if (programmeId !== undefined) {
            updateData.programmeId = programmeId;
        }

        const [updatedUser] = await db
            .update(schema.users)
            .set(updateData)
            .where(eq(schema.users.firebaseUid, decodedToken.uid))
            .returning();

        if (!updatedUser) {
            return NextResponse.json(
                { error: "User not found" },
                { status: 404 }
            );
        }

        return NextResponse.json({
            success: true,
            user: updatedUser,
        });
    } catch (error) {
        console.error("Update profile error:", error);
        return NextResponse.json(
            { error: "Internal server error" },
            { status: 500 }
        );
    }
}
