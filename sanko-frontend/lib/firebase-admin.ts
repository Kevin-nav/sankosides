import { initializeApp, getApps, cert, App } from "firebase-admin/app";
import { getAuth } from "firebase-admin/auth";

function initializeFirebaseAdmin(): App {
    if (getApps().length > 0) {
        return getApps()[0];
    }

    // Use environment variables for credentials
    const projectId = process.env.FIREBASE_PROJECT_ID || process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID;
    const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
    // The private key is stored with escaped newlines in env, we need to unescape them
    const privateKey = process.env.FIREBASE_PRIVATE_KEY?.replace(/\\n/g, "\n");

    if (!projectId || !clientEmail || !privateKey) {
        console.error(
            "Firebase Admin SDK: Missing credentials. Please set FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY in your .env.local file."
        );
        // Return a dummy app that will fail on auth operations - better than crashing the build
        return initializeApp({ projectId: projectId || "dummy" });
    }

    return initializeApp({
        credential: cert({
            projectId,
            clientEmail,
            privateKey,
        }),
    });
}

// Initialize the app
const app = initializeFirebaseAdmin();

// Export the auth instance
export const adminAuth = getAuth(app);

