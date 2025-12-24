import { NextRequest, NextResponse } from "next/server";
import { adminAuth } from "@/lib/firebase-admin";
import { db, schema } from "@/lib/db";
import { eq } from "drizzle-orm";

/**
 * POST /api/auth/sync
 * Syncs a Firebase authenticated user to the Neon database.
 * Called from the frontend after successful Firebase login.
 */
export async function POST(request: NextRequest) {
    try {
        // Get the Firebase ID token from the Authorization header
        const authHeader = request.headers.get("Authorization");
        if (!authHeader || !authHeader.startsWith("Bearer ")) {
            return NextResponse.json(
                { error: "Missing or invalid Authorization header" },
                { status: 401 }
            );
        }

        const idToken = authHeader.split("Bearer ")[1];

        // Verify the token with Firebase Admin
        const decodedToken = await adminAuth.verifyIdToken(idToken);
        const { uid, email, name, picture } = decodedToken;

        if (!email) {
            return NextResponse.json(
                { error: "Email is required" },
                { status: 400 }
            );
        }

        // Check if user already exists in our database
        const existingUsers = await db
            .select()
            .from(schema.users)
            .where(eq(schema.users.firebaseUid, uid))
            .limit(1);

        let user;

        if (existingUsers.length > 0) {
            // Update existing user
            const [updatedUser] = await db
                .update(schema.users)
                .set({
                    email,
                    displayName: name || null,
                    photoUrl: picture || null,
                    updatedAt: new Date(),
                })
                .where(eq(schema.users.firebaseUid, uid))
                .returning();
            user = updatedUser;
        } else {
            // Create new user
            const [newUser] = await db
                .insert(schema.users)
                .values({
                    firebaseUid: uid,
                    email,
                    displayName: name || null,
                    photoUrl: picture || null,
                })
                .returning();
            user = newUser;
        }

        return NextResponse.json({
            success: true,
            user: {
                id: user.id,
                email: user.email,
                displayName: user.displayName,
                subscriptionTier: user.subscriptionTier,
            },
        });
    } catch (error: any) {
        console.error("Auth sync error:", error);

        // Handle database connection errors (Neon serverless timeout, fetch failures)
        if (error.cause?.code === 'UND_ERR_CONNECT_TIMEOUT' ||
            error.message?.includes('fetch failed') ||
            error.message?.includes('Error connecting to database')) {
            return NextResponse.json(
                { error: "Database connection failed. Please try again later." },
                { status: 503 }
            );
        }

        if (error.code === "auth/id-token-expired") {
            return NextResponse.json(
                { error: "Token expired. Please login again." },
                { status: 401 }
            );
        }

        if (error.code === "auth/argument-error") {
            return NextResponse.json(
                { error: "Invalid token format" },
                { status: 401 }
            );
        }

        return NextResponse.json(
            { error: "Internal server error" },
            { status: 500 }
        );
    }
}
