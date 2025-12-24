"use client";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { useTheme } from "next-themes";
import { Loader2, Palette, FileText, AlertTriangle, Check } from "lucide-react";
import { useState, useEffect } from "react";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

export default function SettingsPage() {
    const { user, dbUser, loading, syncUser, signOut } = useAuth();
    const { setTheme } = useTheme();

    // Preferences state
    const [citationStyle, setCitationStyle] = useState("apa");
    const [aspectRatio, setAspectRatio] = useState("16:9");
    const [includeTitleSlide, setIncludeTitleSlide] = useState(true);

    // UI state
    const [savingPrefs, setSavingPrefs] = useState(false);
    const [prefsSaved, setPrefsSaved] = useState(false);
    const [deletingAccount, setDeletingAccount] = useState(false);

    // Initialize from dbUser preferences
    useEffect(() => {
        if (dbUser?.preferences) {
            const prefs = dbUser.preferences as {
                citationStyle?: string;
                aspectRatio?: string;
                includeTitleSlide?: boolean;
            };
            if (prefs.citationStyle) setCitationStyle(prefs.citationStyle);
            if (prefs.aspectRatio) setAspectRatio(prefs.aspectRatio);
            if (prefs.includeTitleSlide !== undefined) setIncludeTitleSlide(prefs.includeTitleSlide);
        }
    }, [dbUser]);

    const handleSavePreferences = async () => {
        if (!user) return;
        setSavingPrefs(true);
        setPrefsSaved(false);

        try {
            const token = await user.getIdToken();
            const res = await fetch("/api/user/preferences", {
                method: "PUT",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    citationStyle,
                    aspectRatio,
                    includeTitleSlide,
                }),
            });

            if (res.ok) {
                await syncUser();
                setPrefsSaved(true);
                setTimeout(() => setPrefsSaved(false), 2000);
            } else {
                console.error("Failed to save preferences");
            }
        } catch (error) {
            console.error("Error saving preferences:", error);
        } finally {
            setSavingPrefs(false);
        }
    };

    const handleDeleteAccount = async () => {
        if (!user) return;
        setDeletingAccount(true);

        try {
            const token = await user.getIdToken();
            const res = await fetch("/api/user", {
                method: "DELETE",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            });

            if (res.ok) {
                // Sign out and redirect to home
                await signOut();
                window.location.href = "/";
            } else {
                console.error("Failed to delete account");
                setDeletingAccount(false);
            }
        } catch (error) {
            console.error("Error deleting account:", error);
            setDeletingAccount(false);
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
                    <h2 className="text-3xl font-bold tracking-tight text-foreground">Settings</h2>
                    <p className="text-muted-foreground">Configure your workspace preferences.</p>
                </div>
            </div>

            <Tabs defaultValue="presentation" className="space-y-6">
                <TabsList className="w-full h-auto p-1 bg-muted grid grid-cols-3 sm:flex sm:h-9 sm:w-fit sm:bg-muted sm:p-1">
                    <TabsTrigger value="presentation" className="data-[state=active]:bg-background data-[state=active]:shadow-sm border-0">
                        <FileText className="h-4 w-4 sm:mr-2" />
                        <span className="hidden sm:inline">Presentation Defaults</span>
                    </TabsTrigger>
                    <TabsTrigger value="appearance" className="data-[state=active]:bg-background data-[state=active]:shadow-sm border-0">
                        <Palette className="h-4 w-4 sm:mr-2" />
                        <span className="hidden sm:inline">Appearance</span>
                    </TabsTrigger>
                    <TabsTrigger value="account" className="data-[state=active]:bg-background data-[state=active]:shadow-sm border-0">
                        <AlertTriangle className="h-4 w-4 sm:mr-2" />
                        <span className="hidden sm:inline">Danger Zone</span>
                    </TabsTrigger>
                </TabsList>

                {/* Presentation Defaults */}
                <TabsContent value="presentation" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Automatic Formatting</CardTitle>
                            <CardDescription>Set your preferred defaults for new projects.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            <div className="grid gap-6 md:grid-cols-2">
                                <div className="space-y-2">
                                    <Label>Default Citation Style</Label>
                                    <Select value={citationStyle} onValueChange={setCitationStyle}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select style" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="apa">APA 7th Edition</SelectItem>
                                            <SelectItem value="mla">MLA 9th Edition</SelectItem>
                                            <SelectItem value="chicago">Chicago Manual of Style</SelectItem>
                                            <SelectItem value="harvard">Harvard</SelectItem>
                                            <SelectItem value="ieee">IEEE</SelectItem>
                                        </SelectContent>
                                    </Select>
                                    <p className="text-xs text-muted-foreground">Applied automatically to synthesis generated slides.</p>
                                </div>
                                <div className="space-y-2">
                                    <Label>Slide Aspect Ratio</Label>
                                    <Select value={aspectRatio} onValueChange={setAspectRatio}>
                                        <SelectTrigger>
                                            <SelectValue placeholder="Select ratio" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="16:9">16:9 (Widescreen)</SelectItem>
                                            <SelectItem value="4:3">4:3 (Standard)</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>
                            </div>

                            <div className="flex items-center justify-between rounded-lg border border-border p-4">
                                <div className="space-y-0.5">
                                    <Label className="text-base">Include Title Slide</Label>
                                    <p className="text-sm text-muted-foreground">Always generate an intro slide with university logo.</p>
                                </div>
                                <Switch
                                    checked={includeTitleSlide}
                                    onCheckedChange={setIncludeTitleSlide}
                                />
                            </div>
                        </CardContent>
                        <CardFooter className="border-t border-border pt-6">
                            <Button onClick={handleSavePreferences} disabled={savingPrefs}>
                                {savingPrefs ? (
                                    <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                                ) : prefsSaved ? (
                                    <><Check className="mr-2 h-4 w-4" /> Saved!</>
                                ) : (
                                    "Save Preferences"
                                )}
                            </Button>
                        </CardFooter>
                    </Card>
                </TabsContent>

                {/* Appearance */}
                <TabsContent value="appearance" className="space-y-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Interface Theme</CardTitle>
                            <CardDescription>Customize how SankoSlides looks on your device.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="space-y-2">
                                <Label>Theme Preference</Label>
                                <Select defaultValue="system" onValueChange={setTheme}>
                                    <SelectTrigger>
                                        <SelectValue placeholder="Select theme" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="dark">Dark (Emerald)</SelectItem>
                                        <SelectItem value="light">Light</SelectItem>
                                        <SelectItem value="system">System</SelectItem>
                                    </SelectContent>
                                </Select>
                            </div>
                        </CardContent>
                    </Card>
                </TabsContent>

                {/* Danger Zone */}
                <TabsContent value="account" className="space-y-6">
                    <Card className="border-destructive/20 bg-destructive/10">
                        <CardHeader>
                            <CardTitle className="text-destructive">Delete Account</CardTitle>
                            <CardDescription className="text-destructive/70">
                                Permanently remove your Personal Account and all of its contents from the SankoSlides platform. This action is not reversible, so please continue with caution.
                            </CardDescription>
                        </CardHeader>
                        <CardFooter className="flex justify-end border-t border-destructive/20 pt-6">
                            <AlertDialog>
                                <AlertDialogTrigger asChild>
                                    <Button variant="destructive" disabled={deletingAccount}>
                                        {deletingAccount ? (
                                            <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Deleting...</>
                                        ) : (
                                            "Delete Personal Account"
                                        )}
                                    </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent className="border-neutral-800 bg-neutral-950">
                                    <AlertDialogHeader>
                                        <AlertDialogTitle className="text-white">Are you absolutely sure?</AlertDialogTitle>
                                        <AlertDialogDescription>
                                            This action cannot be undone. This will permanently delete your account and remove all your data including projects, presentations, and settings.
                                        </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                        <AlertDialogCancel className="bg-neutral-800 text-white border-neutral-700 hover:bg-neutral-700">
                                            Cancel
                                        </AlertDialogCancel>
                                        <AlertDialogAction
                                            onClick={handleDeleteAccount}
                                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                                        >
                                            Yes, delete my account
                                        </AlertDialogAction>
                                    </AlertDialogFooter>
                                </AlertDialogContent>
                            </AlertDialog>
                        </CardFooter>
                    </Card>
                </TabsContent>
            </Tabs>
        </div>
    );
}
