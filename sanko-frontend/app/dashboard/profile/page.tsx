"use client";

import { useAuth } from "@/components/auth-provider";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, School, Check } from "lucide-react";
import { useState, useEffect } from "react";

export default function ProfilePage() {
    const { user, dbUser, loading, syncUser } = useAuth();

    // Form states
    const [displayName, setDisplayName] = useState("");
    const [university, setUniversity] = useState("");
    const [department, setDepartment] = useState("");

    // Loading states
    const [savingProfile, setSavingProfile] = useState(false);
    const [savingAcademic, setSavingAcademic] = useState(false);
    const [profileSaved, setProfileSaved] = useState(false);
    const [academicSaved, setAcademicSaved] = useState(false);

    // Initialize form values from dbUser
    useEffect(() => {
        if (dbUser) {
            setDisplayName(dbUser.displayName || "");
            if (dbUser.universityProfile) {
                const profile = dbUser.universityProfile as { university?: string; department?: string };
                setUniversity(profile.university || "");
                setDepartment(profile.department || "");
            }
        }
    }, [dbUser]);

    const handleSaveProfile = async () => {
        if (!user) return;
        setSavingProfile(true);
        setProfileSaved(false);

        try {
            const token = await user.getIdToken();
            const res = await fetch("/api/user/profile", {
                method: "PUT",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({ displayName }),
            });

            if (res.ok) {
                await syncUser(); // Refresh dbUser state
                setProfileSaved(true);
                setTimeout(() => setProfileSaved(false), 2000);
            } else {
                console.error("Failed to save profile");
            }
        } catch (error) {
            console.error("Error saving profile:", error);
        } finally {
            setSavingProfile(false);
        }
    };

    const handleSaveAcademic = async () => {
        if (!user) return;
        setSavingAcademic(true);
        setAcademicSaved(false);

        try {
            const token = await user.getIdToken();
            const res = await fetch("/api/user/profile", {
                method: "PUT",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    universityProfile: {
                        university,
                        department,
                    },
                }),
            });

            if (res.ok) {
                await syncUser(); // Refresh dbUser state
                setAcademicSaved(true);
                setTimeout(() => setAcademicSaved(false), 2000);
            } else {
                console.error("Failed to save academic info");
            }
        } catch (error) {
            console.error("Error saving academic info:", error);
        } finally {
            setSavingAcademic(false);
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center p-8">
                <Loader2 className="h-8 w-8 animate-spin text-primary" />
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h2 className="text-3xl font-bold tracking-tight text-foreground">Profile</h2>
                    <p className="text-muted-foreground">Manage your public identity and academic credentials.</p>
                </div>
            </div>

            <div className="grid gap-6 md:grid-cols-[300px_1fr]">
                {/* Visual Identity Card */}
                <Card>
                    <CardHeader>
                        <CardTitle>Identity</CardTitle>
                        <CardDescription>How you appear on dashboards.</CardDescription>
                    </CardHeader>
                    <CardContent className="flex flex-col items-center space-y-4">
                        <Avatar className="h-24 w-24 border-2 border-border">
                            <AvatarImage src={user?.photoURL || ""} />
                            <AvatarFallback className="bg-primary/20 text-primary text-xl font-medium">
                                {user?.email?.[0].toUpperCase()}
                            </AvatarFallback>
                        </Avatar>
                        <div className="text-center">
                            <h3 className="font-semibold text-lg text-foreground">{dbUser?.displayName || displayName || "Scholar"}</h3>
                            <p className="text-sm text-muted-foreground">{user?.email}</p>
                        </div>
                        <div className="w-full pt-4">
                            <div className="rounded-lg bg-muted p-3 text-center border border-border">
                                <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-1">Plan</p>
                                <p className="text-primary font-bold">{dbUser?.subscriptionTier === "pro" ? "Pro Scholar" : "Free Tier"}</p>
                            </div>
                            {dbUser?.subscriptionTier !== "pro" && (
                                <Button className="w-full mt-3 bg-gradient-to-r from-emerald-500 to-emerald-700 hover:from-emerald-600 hover:to-emerald-800 text-white shadow-md border-0">
                                    Upgrade to Pro
                                </Button>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Edit Forms */}
                <div className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Personal Information</CardTitle>
                            <CardDescription>Update your contact details.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label>Display Name</Label>
                                <Input
                                    value={displayName}
                                    onChange={(e) => setDisplayName(e.target.value)}
                                    placeholder="Your display name"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Email</Label>
                                <Input
                                    value={user?.email || ""}
                                    disabled
                                    className="opacity-50 cursor-not-allowed"
                                />
                            </div>
                        </CardContent>
                        <CardFooter className="border-t border-border pt-6">
                            <Button
                                className="ml-auto"
                                onClick={handleSaveProfile}
                                disabled={savingProfile}
                            >
                                {savingProfile ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                                ) : profileSaved ? (
                                    <><Check className="mr-2 h-4 w-4" /> Saved!</>
                                ) : (
                                    "Save Changes"
                                )}
                            </Button>
                        </CardFooter>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle className="flex items-center gap-2">
                                <School className="h-5 w-5 text-primary" />
                                Academic Profile
                            </CardTitle>
                            <CardDescription>Used to tailor your citation styles and slide templates.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>University / Institution</Label>
                                    <Input
                                        value={university}
                                        onChange={(e) => setUniversity(e.target.value)}
                                        placeholder="e.g. Stanford University"
                                    />
                                </div>
                                <div className="space-y-2">
                                    <Label>Department / Major</Label>
                                    <Input
                                        value={department}
                                        onChange={(e) => setDepartment(e.target.value)}
                                        placeholder="e.g. Computer Science"
                                    />
                                </div>
                            </div>
                        </CardContent>
                        <CardFooter className="border-t border-border pt-6">
                            <Button
                                variant="outline"
                                className="ml-auto"
                                onClick={handleSaveAcademic}
                                disabled={savingAcademic}
                            >
                                {savingAcademic ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                                ) : academicSaved ? (
                                    <><Check className="mr-2 h-4 w-4" /> Saved!</>
                                ) : (
                                    "Update Academic Info"
                                )}
                            </Button>
                        </CardFooter>
                    </Card>
                </div>
            </div>
        </div>
    );
}
