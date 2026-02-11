"use client";

import { motion } from "framer-motion";
import { ProjectCard } from "./project-card";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface ProjectListProps {
    projects: {
        id: string;
        title: string;
        updatedAt: Date | string;
        slidesCount?: number;
        thumbnailUrl?: string;
        status: string;
        archiveSourceStatus?: string;
    }[];
    onNewProject: () => void;
    showCreateCard?: boolean;
    emptyTitle?: string;
    emptyDescription?: string;
    selectionMode?: boolean;
    selectedIds?: Set<string>;
    onToggleSelect?: (projectId: string) => void;
}

export function ProjectList({
    projects,
    onNewProject,
    showCreateCard = true,
    emptyTitle = "No presentations yet",
    emptyDescription = "Create your first AI-powered presentation.",
    selectionMode = false,
    selectedIds,
    onToggleSelect,
}: ProjectListProps) {
    if (projects.length === 0) {
        return (
            <div className="flex min-h-[400px] flex-col items-center justify-center rounded-lg border border-dashed border-neutral-800 bg-neutral-950 p-8 text-center animate-in fade-in-50">
                <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-neutral-900 border border-neutral-800 mb-6 shadow-xl">
                    <Plus className="h-10 w-10 text-emerald-500" />
                </div>
                <h3 className="mb-2 text-2xl font-bold text-white tracking-tight">{emptyTitle}</h3>
                <p className="mb-8 max-w-sm text-neutral-400 leading-relaxed">
                    {emptyDescription}
                </p>
                {showCreateCard && (
                    <Button onClick={onNewProject} size="lg" className="bg-emerald-600 hover:bg-emerald-500 text-white border border-emerald-500/20 shadow-lg shadow-emerald-900/20">
                        <Plus className="mr-2 h-4 w-4" /> Create Presentation
                    </Button>
                )}
            </div>
        );
    }

    return (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {/* New Project Card */}
            {showCreateCard && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.3 }}
                    onClick={onNewProject}
                    onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                            e.preventDefault();
                            onNewProject();
                        }
                    }}
                    role="button"
                    tabIndex={0}
                    aria-label="Create new project"
                    className="group relative flex cursor-pointer flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-neutral-800 bg-neutral-900/50 p-6 shadow-sm transition-all hover:border-emerald-500/50 hover:bg-neutral-900 hover:shadow-[0_4px_20px_-5px_rgba(16,185,129,0.15)]"
                >
                    <div className="rounded-full bg-neutral-900 p-4 transition-colors group-hover:bg-emerald-500/10 border border-neutral-800 group-hover:border-emerald-500/20">
                        <Plus className="h-8 w-8 text-neutral-400 transition-colors group-hover:text-emerald-400" />
                    </div>
                    <span className="font-semibold text-neutral-400 group-hover:text-emerald-400 transition-colors">
                        New Project
                    </span>
                </motion.div>
            )}

            {/* Project Cards */}
            {projects.map((project, index) => (
                <motion.div
                    key={project.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 + 0.1, duration: 0.4 }}
                >
                    <ProjectCard
                        project={project}
                        selectionMode={selectionMode}
                        selected={selectedIds?.has(project.id) ?? false}
                        onToggleSelect={onToggleSelect ? () => onToggleSelect(project.id) : undefined}
                    />
                </motion.div>
            ))}
        </div>
    );
}
