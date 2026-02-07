"use client";

import { useAuth } from "@/components/auth-provider";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
    SelectGroup,
    SelectLabel,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Loader2, School, Check, GraduationCap, Building2, BookOpen, Info } from "lucide-react";
import { useState, useEffect, useMemo } from "react";
import { useUniversityHierarchy } from "@/hooks/convex";
import { useUpdateProfile } from "@/hooks/api";

// Types for university hierarchy (from single API call)
interface DepartmentHierarchy {
    departmentId: string;
    name: string;
    isStem: boolean;
}

interface FacultyHierarchy {
    facultyId: string;
    name: string;
    shortName: string;
    departments: DepartmentHierarchy[];
}

interface UniversityHierarchy {
    universityId: string;
    name: string;
    shortName: string;
    country: string;
    defaultCitationStyle: string;
    spellingVariant: string;
    unitSystem: string;
    faculties: FacultyHierarchy[];
}

export default function ProfilePage() {
    const { user, convexUser, loading } = useAuth();

    // Form states
    const [displayName, setDisplayName] = useState("");

    // Convex hook - direct query for university hierarchy
    const hierarchy = useUniversityHierarchy() ?? [];
    const loadingHierarchy = hierarchy === undefined;
    const updateProfile = useUpdateProfile();

    // Selection state
    const [selectedUniversity, setSelectedUniversity] = useState<string>("");
    const [selectedFaculty, setSelectedFaculty] = useState<string>("");
    const [selectedDepartment, setSelectedDepartment] = useState<string>("");
    const [selectedAcademicLevel, setSelectedAcademicLevel] = useState<string>("");
    const [selectedAcademicYear, setSelectedAcademicYear] = useState<string>("");

    // Success state for UI feedback
    const [profileSaved, setProfileSaved] = useState(false);
    const [academicSaved, setAcademicSaved] = useState(false);

    // Initialize form values from convexUser
    useEffect(() => {
        if (convexUser) {
            setDisplayName(convexUser.displayName || "");
            const profile = convexUser.universityProfile as {
                universityId?: string;
                facultyId?: string;
                departmentId?: string;
                academicLevel?: string;
                academicYear?: number;
            } | undefined;
            if (profile?.universityId) setSelectedUniversity(profile.universityId);
            if (profile?.facultyId) setSelectedFaculty(profile.facultyId);
            if (profile?.departmentId) setSelectedDepartment(profile.departmentId);
            if (profile?.academicLevel) setSelectedAcademicLevel(profile.academicLevel);
            if (profile?.academicYear) setSelectedAcademicYear(String(profile.academicYear));
        }
    }, [convexUser]);

    // Derived data from hierarchy (no additional fetches needed!)
    const selectedUniversityData = useMemo(() =>
        hierarchy.find(u => u.universityId === selectedUniversity),
        [hierarchy, selectedUniversity]
    );

    const faculties = useMemo(() =>
        selectedUniversityData?.faculties || [],
        [selectedUniversityData]
    );

    const selectedFacultyData = useMemo(() =>
        faculties.find(f => f.facultyId === selectedFaculty),
        [faculties, selectedFaculty]
    );

    const departments = useMemo(() =>
        selectedFacultyData?.departments || [],
        [selectedFacultyData]
    );

    const selectedDepartmentData = useMemo(() =>
        departments.find(d => d.departmentId === selectedDepartment),
        [departments, selectedDepartment]
    );

    const handleUniversityChange = (value: string) => {
        setSelectedUniversity(value);
        setSelectedFaculty("");
        setSelectedDepartment("");
    };

    const handleFacultyChange = (value: string) => {
        setSelectedFaculty(value);
        setSelectedDepartment("");
    };

    const handleSaveProfile = () => {
        if (!user) return;

        updateProfile.mutate(
            { displayName },
            {
                onSuccess: () => {
                    setProfileSaved(true);
                    setTimeout(() => setProfileSaved(false), 2000);
                },
            }
        );
    };

    const handleSaveAcademic = () => {
        if (!user) return;

        updateProfile.mutate(
            {
                universityId: selectedUniversity || null,
                facultyId: selectedFaculty || null,
                departmentId: selectedDepartment || null,
                academicLevel: selectedAcademicLevel || null,
                academicYear: selectedAcademicYear ? parseInt(selectedAcademicYear) : null,
            },
            {
                onSuccess: () => {
                    setAcademicSaved(true);
                    setTimeout(() => setAcademicSaved(false), 2000);
                },
            }
        );
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
                            <h3 className="font-semibold text-lg text-foreground">{convexUser?.displayName || displayName || "Scholar"}</h3>
                            <p className="text-sm text-muted-foreground">{user?.email}</p>
                        </div>

                        {/* University Badge */}
                        {selectedUniversityData && (
                            <div className="w-full">
                                <div className="rounded-lg bg-primary/5 border border-primary/20 p-3 text-center">
                                    <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-1">Institution</p>
                                    <p className="text-primary font-bold">{selectedUniversityData.shortName}</p>
                                    {selectedDepartmentData?.isStem && (
                                        <Badge variant="secondary" className="text-xs mt-1">STEM</Badge>
                                    )}
                                </div>
                            </div>
                        )}

                        <div className="w-full pt-2">
                            <div className="rounded-lg bg-muted p-3 text-center border border-border">
                                <p className="text-xs text-muted-foreground uppercase tracking-wider font-medium mb-1">Plan</p>
                                <p className="text-primary font-bold">{convexUser?.subscriptionTier === "pro" ? "Pro Scholar" : "Free Tier"}</p>
                            </div>
                            {convexUser?.subscriptionTier !== "pro" && (
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
                                disabled={updateProfile.isPending}
                            >
                                {updateProfile.isPending ? (
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
                            <CardDescription>Used to tailor your citation styles, spelling, and slide templates.</CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            {/* University Selection */}
                            <div className="space-y-2">
                                <Label className="flex items-center gap-2">
                                    <Building2 className="h-4 w-4 text-muted-foreground" />
                                    University / Institution
                                </Label>
                                <Select
                                    value={selectedUniversity}
                                    onValueChange={handleUniversityChange}
                                    disabled={loadingHierarchy}
                                >
                                    <SelectTrigger className="w-full">
                                        <SelectValue placeholder={loadingHierarchy ? "Loading..." : "Select your university"} />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectGroup>
                                            <SelectLabel>Supported Universities</SelectLabel>
                                            {hierarchy.map((uni) => (
                                                <SelectItem key={uni.universityId} value={uni.universityId}>
                                                    {uni.name} ({uni.shortName})
                                                </SelectItem>
                                            ))}
                                        </SelectGroup>
                                    </SelectContent>
                                </Select>
                                {hierarchy.length > 0 && !selectedUniversity && (
                                    <p className="text-xs text-muted-foreground">
                                        Can&apos;t find your university? More coming soon!
                                    </p>
                                )}
                            </div>

                            {/* Faculty Selection */}
                            {selectedUniversity && faculties.length > 0 && (
                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2">
                                        <GraduationCap className="h-4 w-4 text-muted-foreground" />
                                        Faculty / School
                                    </Label>
                                    <Select value={selectedFaculty} onValueChange={handleFacultyChange}>
                                        <SelectTrigger className="w-full">
                                            <SelectValue placeholder="Select your faculty" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {faculties.map((faculty) => (
                                                <SelectItem key={faculty.facultyId} value={faculty.facultyId}>
                                                    {faculty.name} ({faculty.shortName})
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}

                            {/* Department Selection */}
                            {selectedFaculty && departments.length > 0 && (
                                <div className="space-y-2">
                                    <Label className="flex items-center gap-2">
                                        <BookOpen className="h-4 w-4 text-muted-foreground" />
                                        Department
                                    </Label>
                                    <Select value={selectedDepartment} onValueChange={setSelectedDepartment}>
                                        <SelectTrigger className="w-full">
                                            <SelectValue placeholder="Select your department" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            {departments.map((dept) => (
                                                <SelectItem key={dept.departmentId} value={dept.departmentId}>
                                                    {dept.name}
                                                    {dept.isStem && " (STEM)"}
                                                </SelectItem>
                                            ))}
                                        </SelectContent>
                                    </Select>
                                </div>
                            )}

                            {/* Academic Level and Year */}
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <div className="space-y-2">
                                    <Label>Academic Level</Label>
                                    <Select value={selectedAcademicLevel} onValueChange={setSelectedAcademicLevel}>
                                        <SelectTrigger className="w-full">
                                            <SelectValue placeholder="Select level" />
                                        </SelectTrigger>
                                        <SelectContent>
                                            <SelectItem value="undergraduate">Undergraduate (BSc)</SelectItem>
                                            <SelectItem value="masters">Masters (MSc/MPhil)</SelectItem>
                                            <SelectItem value="phd">PhD</SelectItem>
                                            <SelectItem value="faculty">Faculty/Staff</SelectItem>
                                        </SelectContent>
                                    </Select>
                                </div>

                                {selectedAcademicLevel === "undergraduate" && (
                                    <div className="space-y-2">
                                        <Label>Academic Year</Label>
                                        <Select value={selectedAcademicYear} onValueChange={setSelectedAcademicYear}>
                                            <SelectTrigger className="w-full">
                                                <SelectValue placeholder="Select year" />
                                            </SelectTrigger>
                                            <SelectContent>
                                                <SelectItem value="1">Year 1 (Freshman)</SelectItem>
                                                <SelectItem value="2">Year 2 (Sophomore)</SelectItem>
                                                <SelectItem value="3">Year 3 (Junior)</SelectItem>
                                                <SelectItem value="4">Year 4 (Senior)</SelectItem>
                                            </SelectContent>
                                        </Select>
                                    </div>
                                )}
                            </div>

                            {/* Info Banner */}
                            {selectedUniversityData && (
                                <div className="rounded-lg bg-primary/5 border border-primary/20 p-4 mt-4">
                                    <div className="flex items-start gap-2">
                                        <Info className="h-4 w-4 text-primary mt-0.5 flex-shrink-0" />
                                        <div className="text-sm">
                                            <p className="font-medium text-foreground mb-1">What this means for your presentations:</p>
                                            <ul className="text-muted-foreground space-y-0.5">
                                                <li>• <span className="font-medium">Citation Style:</span> {selectedUniversityData.defaultCitationStyle}</li>
                                                <li>• <span className="font-medium">Spelling:</span> {selectedUniversityData.spellingVariant}</li>
                                                <li>• <span className="font-medium">Units:</span> {selectedUniversityData.unitSystem}</li>
                                            </ul>
                                        </div>
                                    </div>
                                </div>
                            )}
                        </CardContent>
                        <CardFooter className="border-t border-border pt-6">
                            <Button
                                variant="outline"
                                className="ml-auto"
                                onClick={handleSaveAcademic}
                                disabled={updateProfile.isPending}
                            >
                                {updateProfile.isPending ? (
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
