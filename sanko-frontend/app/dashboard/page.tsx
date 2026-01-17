"use client";

import { useAuth } from "@/components/auth-provider";
import { ProjectList } from "@/components/dashboard/project-list";
import { ModeSelector } from "@/components/dashboard/mode-selector";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useProjects, useCreateProject } from "@/hooks/api";

export default function DashboardPage() {
    const { user } = useAuth();
    const router = useRouter();
    const [detailsOpen, setDetailsOpen] = useState(false);

    // TanStack Query hooks - replaces manual useState/useEffect
    const { data: projects = [], isPending: isLoading } = useProjects();
    const createProject = useCreateProject();

    const handleModeSelect = async (mode: string) => {
        if (!user) return;

        createProject.mutate(
            { title: "New Presentation", mode },
            {
                onSuccess: (data) => {
                    router.push(`/editor/${data.project.id}`);
                },
            }
        );
    };

    if (isLoading) {
        return (
            <div className="flex h-full w-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
            </div>
        );
    }

    return (
        <div className="flex flex-col space-y-8 p-4 md:p-8 pt-6">
            <div className="flex items-center justify-between space-y-2">
                <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white">Dashboard</h2>
            </div>

            <ProjectList
                projects={projects}
                onNewProject={() => setDetailsOpen(true)}
            />

            {/* Mode Selection Modal */}
            <Dialog open={detailsOpen} onOpenChange={setDetailsOpen}>
                <DialogContent className="w-[95vw] max-w-xl border-neutral-800 bg-neutral-950 p-6 shadow-2xl max-h-[85vh] overflow-y-auto scrollbar-dark">
                    <DialogHeader className="mb-6">
                        <DialogTitle className="text-3xl font-bold text-white">Choose your Engine</DialogTitle>
                        <DialogDescription className="text-neutral-400 text-lg">
                            Select the best generation mode for your needs.
                        </DialogDescription>
                    </DialogHeader>

                    <ModeSelector onSelect={handleModeSelect} />

                </DialogContent>
            </Dialog>
        </div>
    );
}

