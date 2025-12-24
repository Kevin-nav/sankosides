import { NextRequest, NextResponse } from "next/server";
import { adminAuth } from "@/lib/firebase-admin";
import { db, schema } from "@/lib/db";
import { eq } from "drizzle-orm";

/**
 * PUT /api/user/preferences
 * Updates the user's presentation preferences (stored in preferences JSONB column)
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
        const { citationStyle, aspectRatio, includeTitleSlide } = body;

        // Get existing user to merge preferences
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

        // Merge with existing preferences
        const existingPrefs = (users[0].preferences as Record<string, unknown>) || {};
        const newPreferences = {
            ...existingPrefs,
            ...(citationStyle !== undefined && { citationStyle }),
            ...(aspectRatio !== undefined && { aspectRatio }),
            ...(includeTitleSlide !== undefined && { includeTitleSlide }),
        };

        const [updatedUser] = await db
            .update(schema.users)
            .set({
                preferences: newPreferences,
                updatedAt: new Date(),
            })
            .where(eq(schema.users.firebaseUid, decodedToken.uid))
            .returning();

        return NextResponse.json({
            success: true,
            preferences: updatedUser.preferences,
        });
    } catch (error) {
        console.error("Update preferences error:", error);
        return NextResponse.json(
            { error: "Internal server error" },
            { status: 500 }
        );
    }
}
