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

// Types for our database user (synced from Neon)
type DbUser = {
    id: string;
    email: string;
    displayName: string | null;
    subscriptionTier: string;
    universityProfile: any | null;
};

type AuthContextType = {
    user: User | null;
    dbUser: DbUser | null;
    loading: boolean;
    loginWithEmail: (email: string, password: string) => Promise<void>;
    registerWithEmail: (email: string, password: string) => Promise<void>;
    loginWithGoogle: () => Promise<void>;
    signOut: () => Promise<void>;
    syncUser: () => Promise<void>;
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
    const [dbUser, setDbUser] = useState<DbUser | null>(null);
    const [loading, setLoading] = useState(true);

    // Sync the Firebase user to our Neon database
    const syncUser = useCallback(async () => {
        if (!user) {
            setDbUser(null);
            return;
        }

        try {
            const idToken = await user.getIdToken();
            const response = await fetch("/api/auth/sync", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${idToken}`,
                    "Content-Type": "application/json",
                },
            });

            if (response.ok) {
                const data = await response.json();
                setDbUser(data.user);
            } else {
                console.error("Failed to sync user:", await response.text());
            }
        } catch (error) {
            console.error("Error syncing user:", error);
        }
    }, [user]);

    // Listen to Firebase auth state changes
    useEffect(() => {
        const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
            setUser(firebaseUser);
            setLoading(false);
        });
        return () => unsubscribe();
    }, []);

    // Sync user to database when Firebase user changes
    useEffect(() => {
        if (user) {
            syncUser();
        } else {
            setDbUser(null);
        }
    }, [user, syncUser]);

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
        setDbUser(null);
    };

    return (
        <AuthContext.Provider
            value={{
                user,
                dbUser,
                loading,
                loginWithEmail,
                registerWithEmail,
                loginWithGoogle,
                signOut,
                syncUser,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

