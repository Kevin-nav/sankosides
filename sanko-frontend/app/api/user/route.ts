import { NextRequest, NextResponse } from "next/server";
import { adminAuth } from "@/lib/firebase-admin";
import { db, schema } from "@/lib/db";
import { eq } from "drizzle-orm";

/**
 * DELETE /api/user
 * Permanently deletes the user's account from both the database and Firebase Auth.
 * This action is irreversible and will:
 * 1. Delete all projects associated with the user
 * 2. Delete the user record from the database
 * 3. Delete the user from Firebase Authentication
 */
export async function DELETE(request: NextRequest) {
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
        const firebaseUid = decodedToken.uid;

        // Find the user in our database
        const users = await db
            .select()
            .from(schema.users)
            .where(eq(schema.users.firebaseUid, firebaseUid))
            .limit(1);

        if (users.length === 0) {
            return NextResponse.json(
                { error: "User not found" },
                { status: 404 }
            );
        }

        const userId = users[0].id;

        // Delete all projects belonging to this user
        // (The ON DELETE CASCADE should handle this, but let's be explicit)
        await db
            .delete(schema.projects)
            .where(eq(schema.projects.userId, userId));

        // Delete the user from our database
        await db
            .delete(schema.users)
            .where(eq(schema.users.id, userId));

        // Delete the user from Firebase Authentication
        try {
            await adminAuth.deleteUser(firebaseUid);
        } catch (firebaseError) {
            // Log but don't fail - the DB deletion is more important
            console.error("Failed to delete user from Firebase:", firebaseError);
        }

        return NextResponse.json({
            success: true,
            message: "Account deleted successfully",
        });
    } catch (error) {
        console.error("Delete account error:", error);
        return NextResponse.json(
            { error: "Internal server error" },
            { status: 500 }
        );
    }
}
