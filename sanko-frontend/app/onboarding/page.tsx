"use client";

import { useAuth } from "@/components/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
import {
    Loader2,
    School,
    Check,
    GraduationCap,
    Building2,
    BookOpen,
    ChevronRight,
    ChevronLeft,
    Sparkles,
    ArrowRight
} from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";

// Types for university data
interface University {
    university_id: string;
    name: string;
    short_name: string;
    country: string;
    faculty_count: number;
    department_count: number;
    programme_count: number;
}

interface Faculty {
    faculty_id: string;
    name: string;
    short_name: string;
}

interface Department {
    department_id: string;
    name: string;
    is_stem: boolean;
}

type OnboardingStep = "welcome" | "university" | "faculty" | "department" | "level" | "complete";

export default function OnboardingPage() {
    const { user, syncUser } = useAuth();
    const router = useRouter();

    // Step state
    const [currentStep, setCurrentStep] = useState<OnboardingStep>("welcome");

    // University data
    const [universities, setUniversities] = useState<University[]>([]);
    const [faculties, setFaculties] = useState<Faculty[]>([]);
    const [departments, setDepartments] = useState<Department[]>([]);

    // Selection state
    const [selectedUniversity, setSelectedUniversity] = useState<string>("");
    const [selectedFaculty, setSelectedFaculty] = useState<string>("");
    const [selectedDepartment, setSelectedDepartment] = useState<string>("");
    const [selectedAcademicLevel, setSelectedAcademicLevel] = useState<string>("");
    const [selectedAcademicYear, setSelectedAcademicYear] = useState<string>("");

    // Loading states
    const [loadingUniversities, setLoadingUniversities] = useState(true);
    const [loadingFaculties, setLoadingFaculties] = useState(false);
    const [loadingDepartments, setLoadingDepartments] = useState(false);
    const [saving, setSaving] = useState(false);

    // Fetch universities on mount
    useEffect(() => {
        async function fetchUniversities() {
            try {
                const res = await fetch("/api/universities");
                if (res.ok) {
                    const data = await res.json();
                    setUniversities(data);
                }
            } catch (error) {
                console.error("Error fetching universities:", error);
            } finally {
                setLoadingUniversities(false);
            }
        }
        fetchUniversities();
    }, []);

    // Fetch faculties when university changes
    const fetchFaculties = useCallback(async (universityId: string) => {
        if (!universityId) return;

        setLoadingFaculties(true);
        try {
            const res = await fetch(`/api/universities/${universityId}/faculties`);
            if (res.ok) {
                const data = await res.json();
                setFaculties(data);
            }
        } catch (error) {
            console.error("Error fetching faculties:", error);
        } finally {
            setLoadingFaculties(false);
        }
    }, []);

    // Fetch departments when faculty changes
    const fetchDepartments = useCallback(async (universityId: string, facultyId: string) => {
        if (!universityId || !facultyId) return;

        setLoadingDepartments(true);
        try {
            const res = await fetch(`/api/universities/${universityId}/faculties/${facultyId}/departments`);
            if (res.ok) {
                const data = await res.json();
                setDepartments(data);
            }
        } catch (error) {
            console.error("Error fetching departments:", error);
        } finally {
            setLoadingDepartments(false);
        }
    }, []);

    // Auto-fetch faculties when university selected and moving to faculty step
    useEffect(() => {
        if (currentStep === "faculty" && selectedUniversity) {
            fetchFaculties(selectedUniversity);
        }
    }, [currentStep, selectedUniversity, fetchFaculties]);

    // Auto-fetch departments when faculty selected and moving to department step
    useEffect(() => {
        if (currentStep === "department" && selectedUniversity && selectedFaculty) {
            fetchDepartments(selectedUniversity, selectedFaculty);
        }
    }, [currentStep, selectedUniversity, selectedFaculty, fetchDepartments]);

    const handleUniversitySelect = (value: string) => {
        setSelectedUniversity(value);
        setSelectedFaculty("");
        setSelectedDepartment("");
        setFaculties([]);
        setDepartments([]);
    };

    const handleFacultySelect = (value: string) => {
        setSelectedFaculty(value);
        setSelectedDepartment("");
        setDepartments([]);
    };

    const handleComplete = async () => {
        if (!user) return;
        setSaving(true);

        try {
            const token = await user.getIdToken();
            const res = await fetch("/api/user/profile", {
                method: "PUT",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    universityId: selectedUniversity,
                    facultyId: selectedFaculty,
                    departmentId: selectedDepartment,
                    academicLevel: selectedAcademicLevel,
                    academicYear: selectedAcademicYear ? parseInt(selectedAcademicYear) : null,
                }),
            });

            if (res.ok) {
                await syncUser();
                setCurrentStep("complete");
            } else {
                console.error("Failed to save onboarding data");
            }
        } catch (error) {
            console.error("Error during onboarding:", error);
        } finally {
            setSaving(false);
        }
    };

    const goToDashboard = () => {
        router.push("/dashboard");
    };

    // Get details for display
    const selectedUniversityDetails = universities.find(u => u.university_id === selectedUniversity);
    const selectedFacultyDetails = faculties.find(f => f.faculty_id === selectedFaculty);
    const selectedDepartmentDetails = departments.find(d => d.department_id === selectedDepartment);

    // Step navigation helpers
    const canProceed = () => {
        switch (currentStep) {
            case "welcome": return true;
            case "university": return !!selectedUniversity;
            case "faculty": return !!selectedFaculty;
            case "department": return !!selectedDepartment;
            case "level": return !!selectedAcademicLevel;
            default: return false;
        }
    };

    const nextStep = () => {
        switch (currentStep) {
            case "welcome": setCurrentStep("university"); break;
            case "university": setCurrentStep("faculty"); break;
            case "faculty": setCurrentStep("department"); break;
            case "department": setCurrentStep("level"); break;
            case "level": handleComplete(); break;
        }
    };

    const prevStep = () => {
        switch (currentStep) {
            case "university": setCurrentStep("welcome"); break;
            case "faculty": setCurrentStep("university"); break;
            case "department": setCurrentStep("faculty"); break;
            case "level": setCurrentStep("department"); break;
        }
    };

    const stepProgress = () => {
        const steps = ["welcome", "university", "faculty", "department", "level", "complete"];
        return ((steps.indexOf(currentStep) + 1) / steps.length) * 100;
    };

    return (
        <div className="min-h-screen bg-gradient-to-b from-background to-muted/30 flex items-center justify-center p-4">
            <div className="w-full max-w-lg">
                {/* Progress Bar */}
                {currentStep !== "complete" && (
                    <div className="mb-8">
                        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
                            <div
                                className="h-full bg-primary transition-all duration-500 ease-out"
                                style={{ width: `${stepProgress()}%` }}
                            />
                        </div>
                    </div>
                )}

                {/* Welcome Step */}
                {currentStep === "welcome" && (
                    <Card className="border-0 shadow-xl">
                        <CardHeader className="text-center pb-2">
                            <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-primary/10 flex items-center justify-center">
                                <Sparkles className="h-8 w-8 text-primary" />
                            </div>
                            <CardTitle className="text-2xl">Welcome to SankoSlides</CardTitle>
                            <CardDescription className="text-base">
                                Let&apos;s personalize your experience by setting up your academic profile.
                                This helps us tailor citations, formatting, and more.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="pt-6">
                            <Button
                                className="w-full h-12 text-lg"
                                onClick={nextStep}
                            >
                                Get Started
                                <ChevronRight className="ml-2 h-5 w-5" />
                            </Button>
                        </CardContent>
                    </Card>
                )}

                {/* University Step */}
                {currentStep === "university" && (
                    <Card className="border-0 shadow-xl">
                        <CardHeader className="text-center pb-4">
                            <div className="mx-auto mb-4 h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
                                <Building2 className="h-7 w-7 text-primary" />
                            </div>
                            <CardTitle className="text-xl">Select Your University</CardTitle>
                            <CardDescription>
                                We&apos;ll apply your institution&apos;s formatting standards automatically.
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Select
                                value={selectedUniversity}
                                onValueChange={handleUniversitySelect}
                                disabled={loadingUniversities}
                            >
                                <SelectTrigger className="w-full h-12">
                                    <SelectValue placeholder={loadingUniversities ? "Loading universities..." : "Choose your university"} />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectGroup>
                                        <SelectLabel>Available Universities</SelectLabel>
                                        {universities.map((uni) => (
                                            <SelectItem key={uni.university_id} value={uni.university_id}>
                                                <div className="flex items-center gap-2">
                                                    <span>{uni.name}</span>
                                                    <Badge variant="secondary" className="text-xs">
                                                        {uni.short_name}
                                                    </Badge>
                                                </div>
                                            </SelectItem>
                                        ))}
                                    </SelectGroup>
                                </SelectContent>
                            </Select>

                            {selectedUniversityDetails && (
                                <div className="rounded-lg bg-primary/5 border border-primary/20 p-4">
                                    <p className="text-sm text-muted-foreground">
                                        <span className="font-medium text-foreground">{selectedUniversityDetails.faculty_count}</span> faculties,
                                        <span className="font-medium text-foreground"> {selectedUniversityDetails.programme_count}</span> programmes
                                    </p>
                                </div>
                            )}

                            <div className="flex gap-3 pt-4">
                                <Button variant="outline" onClick={prevStep} className="flex-1">
                                    <ChevronLeft className="mr-2 h-4 w-4" />
                                    Back
                                </Button>
                                <Button onClick={nextStep} disabled={!canProceed()} className="flex-1">
                                    Continue
                                    <ChevronRight className="ml-2 h-4 w-4" />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Faculty Step */}
                {currentStep === "faculty" && (
                    <Card className="border-0 shadow-xl">
                        <CardHeader className="text-center pb-4">
                            <div className="mx-auto mb-4 h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
                                <GraduationCap className="h-7 w-7 text-primary" />
                            </div>
                            <CardTitle className="text-xl">Select Your Faculty</CardTitle>
                            <CardDescription>
                                Which faculty or school are you in at {selectedUniversityDetails?.short_name}?
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Select
                                value={selectedFaculty}
                                onValueChange={handleFacultySelect}
                                disabled={loadingFaculties}
                            >
                                <SelectTrigger className="w-full h-12">
                                    <SelectValue placeholder={loadingFaculties ? "Loading faculties..." : "Choose your faculty"} />
                                </SelectTrigger>
                                <SelectContent>
                                    {faculties.map((faculty) => (
                                        <SelectItem key={faculty.faculty_id} value={faculty.faculty_id}>
                                            <div className="flex items-center gap-2">
                                                <span>{faculty.name}</span>
                                                <Badge variant="outline" className="text-xs">
                                                    {faculty.short_name}
                                                </Badge>
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>

                            <div className="flex gap-3 pt-4">
                                <Button variant="outline" onClick={prevStep} className="flex-1">
                                    <ChevronLeft className="mr-2 h-4 w-4" />
                                    Back
                                </Button>
                                <Button onClick={nextStep} disabled={!canProceed()} className="flex-1">
                                    Continue
                                    <ChevronRight className="ml-2 h-4 w-4" />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Department Step */}
                {currentStep === "department" && (
                    <Card className="border-0 shadow-xl">
                        <CardHeader className="text-center pb-4">
                            <div className="mx-auto mb-4 h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
                                <BookOpen className="h-7 w-7 text-primary" />
                            </div>
                            <CardTitle className="text-xl">Select Your Department</CardTitle>
                            <CardDescription>
                                Which department within {selectedFacultyDetails?.short_name}?
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Select
                                value={selectedDepartment}
                                onValueChange={setSelectedDepartment}
                                disabled={loadingDepartments}
                            >
                                <SelectTrigger className="w-full h-12">
                                    <SelectValue placeholder={loadingDepartments ? "Loading departments..." : "Choose your department"} />
                                </SelectTrigger>
                                <SelectContent>
                                    {departments.map((dept) => (
                                        <SelectItem key={dept.department_id} value={dept.department_id}>
                                            <div className="flex items-center gap-2">
                                                <span>{dept.name}</span>
                                                {dept.is_stem && (
                                                    <Badge variant="secondary" className="text-xs">STEM</Badge>
                                                )}
                                            </div>
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>

                            <div className="flex gap-3 pt-4">
                                <Button variant="outline" onClick={prevStep} className="flex-1">
                                    <ChevronLeft className="mr-2 h-4 w-4" />
                                    Back
                                </Button>
                                <Button onClick={nextStep} disabled={!canProceed()} className="flex-1">
                                    Continue
                                    <ChevronRight className="ml-2 h-4 w-4" />
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Academic Level Step */}
                {currentStep === "level" && (
                    <Card className="border-0 shadow-xl">
                        <CardHeader className="text-center pb-4">
                            <div className="mx-auto mb-4 h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
                                <School className="h-7 w-7 text-primary" />
                            </div>
                            <CardTitle className="text-xl">Academic Level</CardTitle>
                            <CardDescription>
                                What&apos;s your current academic standing?
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <Select
                                value={selectedAcademicLevel}
                                onValueChange={setSelectedAcademicLevel}
                            >
                                <SelectTrigger className="w-full h-12">
                                    <SelectValue placeholder="Select your level" />
                                </SelectTrigger>
                                <SelectContent>
                                    <SelectItem value="undergraduate">Undergraduate (BSc)</SelectItem>
                                    <SelectItem value="masters">Masters (MSc/MPhil)</SelectItem>
                                    <SelectItem value="phd">PhD</SelectItem>
                                    <SelectItem value="faculty">Faculty/Staff</SelectItem>
                                </SelectContent>
                            </Select>

                            {selectedAcademicLevel === "undergraduate" && (
                                <Select
                                    value={selectedAcademicYear}
                                    onValueChange={setSelectedAcademicYear}
                                >
                                    <SelectTrigger className="w-full h-12">
                                        <SelectValue placeholder="Select your year" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        <SelectItem value="1">Year 1 (Freshman)</SelectItem>
                                        <SelectItem value="2">Year 2 (Sophomore)</SelectItem>
                                        <SelectItem value="3">Year 3 (Junior)</SelectItem>
                                        <SelectItem value="4">Year 4 (Senior)</SelectItem>
                                    </SelectContent>
                                </Select>
                            )}

                            <div className="flex gap-3 pt-4">
                                <Button variant="outline" onClick={prevStep} className="flex-1">
                                    <ChevronLeft className="mr-2 h-4 w-4" />
                                    Back
                                </Button>
                                <Button
                                    onClick={nextStep}
                                    disabled={!canProceed() || saving}
                                    className="flex-1"
                                >
                                    {saving ? (
                                        <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Saving...</>
                                    ) : (
                                        <>
                                            Complete Setup
                                            <Check className="ml-2 h-4 w-4" />
                                        </>
                                    )}
                                </Button>
                            </div>
                        </CardContent>
                    </Card>
                )}

                {/* Complete Step */}
                {currentStep === "complete" && (
                    <Card className="border-0 shadow-xl">
                        <CardHeader className="text-center pb-4">
                            <div className="mx-auto mb-4 h-16 w-16 rounded-full bg-emerald-500/10 flex items-center justify-center">
                                <Check className="h-8 w-8 text-emerald-500" />
                            </div>
                            <CardTitle className="text-2xl">You&apos;re All Set!</CardTitle>
                            <CardDescription className="text-base">
                                Your academic profile is configured. Here&apos;s what we&apos;ll automatically apply:
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-4">
                            <div className="rounded-lg bg-muted p-4 space-y-2">
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">Institution</span>
                                    <span className="font-medium">{selectedUniversityDetails?.short_name}</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">Citation Style</span>
                                    <span className="font-medium">Harvard</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">Spelling</span>
                                    <span className="font-medium">British English</span>
                                </div>
                                <div className="flex justify-between text-sm">
                                    <span className="text-muted-foreground">Units</span>
                                    <span className="font-medium">SI System</span>
                                </div>
                                {selectedDepartmentDetails?.is_stem && (
                                    <div className="flex justify-between text-sm">
                                        <span className="text-muted-foreground">Department Type</span>
                                        <Badge variant="secondary">STEM</Badge>
                                    </div>
                                )}
                            </div>

                            <Button
                                className="w-full h-12 text-lg bg-gradient-to-r from-emerald-500 to-emerald-700 hover:from-emerald-600 hover:to-emerald-800"
                                onClick={goToDashboard}
                            >
                                Go to Dashboard
                                <ArrowRight className="ml-2 h-5 w-5" />
                            </Button>
                        </CardContent>
                    </Card>
                )}
            </div>
        </div>
    );
}
