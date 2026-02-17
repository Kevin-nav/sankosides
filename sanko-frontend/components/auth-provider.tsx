"use client";

import { createContext, useContext, useEffect, useState, useCallback } from "react";
import {
    User,
    onAuthStateChanged,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signInWithPopup,
    GoogleAuthProvider,
    signOut as firebaseSignOut,
} from "firebase/auth";
import { auth } from "@/lib/firebase";
import { useMutation, useQuery } from "convex/react";
import { api } from "@/convex/_generated/api";
import { Id } from "@/convex/_generated/dataModel";
import posthog from "posthog-js";

// Types for our Convex user
type ConvexUser = {
    _id: Id<"users">;
    firebaseUid: string;
    email: string;
    displayName?: string;
    photoUrl?: string;
    subscriptionTier?: string;
    universityProfile?: Record<string, unknown>;
    preferences?: {
        theme?: string;
        citationStyle?: string;
        aspectRatio?: string;
        language?: string;
        marketingEmails?: boolean;
    };
    createdAt: number;
    updatedAt: number;
};

type AuthContextType = {
    user: User | null;
    convexUser: ConvexUser | null;
    convexUserId: Id<"users"> | null;
    loading: boolean;
    loginWithEmail: (email: string, password: string) => Promise<void>;
    registerWithEmail: (email: string, password: string) => Promise<void>;
    loginWithGoogle: () => Promise<void>;
    signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthContextType | null>(null);

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error("useAuth must be used within an AuthProvider");
    }
    return context;
};

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [firebaseUid, setFirebaseUid] = useState<string | null>(null);

    // Convex mutation to sync user
    const syncUserMutation = useMutation(api.users.syncUser);

    // Convex query to get user data - real-time subscription!
    const convexUser = useQuery(
        api.users.getUser,
        firebaseUid ? { firebaseUid } : "skip"
    ) as ConvexUser | null | undefined;

    // Sync user to Convex when Firebase auth changes
    const syncToConvex = useCallback(async (firebaseUser: User) => {
        try {
            await syncUserMutation({
                firebaseUid: firebaseUser.uid,
                email: firebaseUser.email || "",
                displayName: firebaseUser.displayName || undefined,
                photoUrl: firebaseUser.photoURL || undefined,
            });
        } catch (error) {
            console.error("Error syncing user to Convex:", error);
        }
    }, [syncUserMutation]);

    // Listen to Firebase auth state changes
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
            setUser(firebaseUser);
            setFirebaseUid(firebaseUser?.uid || null);

            if (firebaseUser) {
                // Sync to Convex - creates user if doesn't exist
                await syncToConvex(firebaseUser);
                try {
                    if (process.env.NEXT_PUBLIC_POSTHOG_KEY) {
                        posthog.identify(firebaseUser.uid, {
                            email: firebaseUser.email || undefined,
                            name: firebaseUser.displayName || undefined,
                        });
                    }
                } catch {
                    // Best-effort; do not block auth flows.
                }
            }

            setLoading(false);
        });
        return () => unsubscribe();
    }, [syncToConvex]);

    // Auth functions
    const loginWithEmail = async (email: string, password: string) => {
        await signInWithEmailAndPassword(auth, email, password);
    };

    const registerWithEmail = async (email: string, password: string) => {
        await createUserWithEmailAndPassword(auth, email, password);
    };

    const loginWithGoogle = async () => {
        const provider = new GoogleAuthProvider();
        await signInWithPopup(auth, provider);
    };

    const signOut = async () => {
        await firebaseSignOut(auth);
        try {
            if (process.env.NEXT_PUBLIC_POSTHOG_KEY) {
                posthog.reset();
            }
        } catch {
            // ignore
        }
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                convexUser: convexUser ?? null,
                convexUserId: convexUser?._id ?? null,
                loading,
                loginWithEmail,
                registerWithEmail,
                loginWithGoogle,
                signOut,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}
