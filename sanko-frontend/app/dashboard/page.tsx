"use client";

import { useMemo, useState } from "react";
import { useAuth } from "@/components/auth-provider";
import { ProjectList } from "@/components/dashboard/project-list";
import { Loader2, CheckSquare, Square, Archive, ArchiveRestore, Trash2, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { Id, useCreateProject, useDeleteProject, useUpdateProject, useUserProjects } from "@/hooks/convex";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/toast";

function generateNextUntitledName(existingTitles: string[]): string {
    const base = "Untitled Presentation";
    const used = new Set(existingTitles.map((title) => title.trim().toLowerCase()));
    if (!used.has(base.toLowerCase())) return base;

    let index = 2;
    while (used.has(`${base} ${index}`.toLowerCase())) {
        index += 1;
    }
    return `${base} ${index}`;
}

export default function DashboardPage() {
    const { loading, convexUserId } = useAuth();
    const router = useRouter();
    const { toast } = useToast();
    const projects = useUserProjects(convexUserId);
    const createProject = useCreateProject();
    const updateProject = useUpdateProject();
    const deleteProject = useDeleteProject();
    const [view, setView] = useState<"active" | "archived">("active");
    const [selectionMode, setSelectionMode] = useState(false);
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
    const [bulkBusy, setBulkBusy] = useState(false);
    const [optimisticDeletedIds, setOptimisticDeletedIds] = useState<Set<string>>(new Set());
    const [bulkProgress, setBulkProgress] = useState<{ done: number; total: number } | null>(null);

    const mappedProjects = useMemo(() => (
        (projects || []).map((project) => ({
            id: project._id,
            title: project.title,
            updatedAt: new Date(project.updatedAt).toISOString(),
            status: project.status,
            thumbnailUrl: project.thumbnailUrl,
            archiveSourceStatus: (project as { archiveSourceStatus?: string }).archiveSourceStatus,
        }))
    ), [projects]);

    const visibleMappedProjects = mappedProjects.filter((project) => !optimisticDeletedIds.has(project.id));
    const activeProjects = visibleMappedProjects.filter((project) => project.status !== "archived");
    const archivedProjects = visibleMappedProjects.filter((project) => project.status === "archived");
    const visibleProjects = view === "active" ? activeProjects : archivedProjects;
    const selectedProjects = visibleProjects.filter((project) => selectedIds.has(project.id));
    const allVisibleSelected = visibleProjects.length > 0 && selectedProjects.length === visibleProjects.length;

    const clearSelection = () => setSelectedIds(new Set());

    const toggleSelectionMode = () => {
        setSelectionMode((prev) => !prev);
        clearSelection();
    };

    const toggleProjectSelection = (projectId: string) => {
        setSelectedIds((prev) => {
            const next = new Set(prev);
            if (next.has(projectId)) {
                next.delete(projectId);
            } else {
                next.add(projectId);
            }
            return next;
        });
    };

    const toggleSelectAllVisible = () => {
        if (allVisibleSelected) {
            clearSelection();
            return;
        }
        setSelectedIds(new Set(visibleProjects.map((project) => project.id)));
    };

    const handleCreateProject = async () => {
        if (!convexUserId) return;

        try {
            const nextTitle = generateNextUntitledName(mappedProjects.map((project) => project.title));
            const projectId = await createProject({
                title: nextTitle,
                userId: convexUserId,
            });
            router.push(`/editor/${projectId}`);
        } catch (error) {
            console.error("Failed to create project:", error);
        }
    };

    const runBulkAction = async (action: () => Promise<void>) => {
        if (bulkBusy || selectedProjects.length === 0) return;
        setBulkBusy(true);
        setBulkProgress(null);
        try {
            await action();
            clearSelection();
            setSelectionMode(false);
        } catch (error) {
            console.error("Bulk action failed:", error);
            toast({
                title: "Bulk action failed",
                description: "Some selected projects could not be processed. Please retry.",
                variant: "error",
            });
        } finally {
            setBulkProgress(null);
            setBulkBusy(false);
        }
    };

    const handleBulkArchive = async () => runBulkAction(async () => {
        const candidates = selectedProjects.filter((project) => project.status !== "generating");
        const skipped = selectedProjects.length - candidates.length;
        await Promise.all(
            candidates.map((project) => updateProject({
                id: project.id as Id<"projects">,
                status: "archived",
                archiveSourceStatus: project.status,
            }))
        );
        toast({
            title: "Archive complete",
            description: skipped > 0
                ? `Archived ${candidates.length}. Skipped ${skipped} generating project(s).`
                : `Archived ${candidates.length} project(s).`,
            variant: "success",
        });
    });

    const handleBulkUnarchive = async () => runBulkAction(async () => {
        await Promise.all(
            selectedProjects.map((project) => {
                const restoreStatus = project.archiveSourceStatus || "draft";
                return updateProject({
                    id: project.id as Id<"projects">,
                    status: restoreStatus,
                    clearArchiveSourceStatus: true,
                });
            })
        );
        toast({
            title: "Restore complete",
            description: `Restored ${selectedProjects.length} project(s).`,
            variant: "success",
        });
    });

    const handleBulkDelete = async () => runBulkAction(async () => {
        const deletable = selectedProjects.filter((project) => project.status !== "generating");
        const deletingIds = new Set(deletable.map((project) => project.id));
        const skipped = selectedProjects.length - deletable.length;
        const failedIds: string[] = [];

        setOptimisticDeletedIds((prev) => new Set([...prev, ...deletingIds]));
        setBulkProgress({ done: 0, total: deletable.length });

        let done = 0;
        for (const project of deletable) {
            try {
                await deleteProject({ id: project.id as Id<"projects"> });
            } catch (error) {
                console.error(`Bulk delete failed for ${project.id}:`, error);
                failedIds.push(project.id);
            } finally {
                done += 1;
                setBulkProgress({ done, total: deletable.length });
            }
        }

        if (failedIds.length > 0) {
            setOptimisticDeletedIds((prev) => {
                const next = new Set(prev);
                for (const id of failedIds) next.delete(id);
                return next;
            });
            throw new Error(`Failed to delete ${failedIds.length} project(s)`);
        }

        toast({
            title: "Delete complete",
            description: skipped > 0
                ? `Deleted ${deletable.length}. Skipped ${skipped} generating project(s).`
                : `Deleted ${deletable.length} project(s).`,
            variant: "success",
        });
    });

    if (loading || projects === undefined) {
        return (
            <div className="flex h-full w-full items-center justify-center">
                <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
            </div>
        );
    }

    return (
        <div className="flex flex-col space-y-8 p-4 md:p-8 pt-6">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white">Dashboard</h2>
                <div className="flex w-full flex-wrap items-center gap-2 md:w-auto">
                    <Button
                        variant={view === "active" ? "default" : "outline"}
                        className={view === "active" ? "bg-emerald-600 hover:bg-emerald-500 text-white" : "border-neutral-700 text-neutral-300"}
                        onClick={() => {
                            setView("active");
                            clearSelection();
                        }}
                    >
                        Active ({activeProjects.length})
                    </Button>
                    <Button
                        variant={view === "archived" ? "default" : "outline"}
                        className={view === "archived" ? "bg-amber-600 hover:bg-amber-500 text-white" : "border-neutral-700 text-neutral-300"}
                        onClick={() => {
                            setView("archived");
                            clearSelection();
                        }}
                    >
                        Archived ({archivedProjects.length})
                    </Button>
                </div>
            </div>

            <div className="flex w-full flex-wrap items-center gap-2">
                <Button
                    variant={selectionMode ? "default" : "outline"}
                    className={selectionMode ? "bg-blue-600 hover:bg-blue-500 text-white" : "border-neutral-700 text-neutral-300"}
                    onClick={toggleSelectionMode}
                >
                    {selectionMode ? <X className="mr-2 h-4 w-4" /> : <CheckSquare className="mr-2 h-4 w-4" />}
                    {selectionMode ? "Exit select" : "Select"}
                </Button>

                {selectionMode && (
                    <>
                        <Button
                            variant="outline"
                            className="border-neutral-700 text-neutral-300"
                            onClick={toggleSelectAllVisible}
                            disabled={bulkBusy || visibleProjects.length === 0}
                        >
                            {allVisibleSelected ? <Square className="mr-2 h-4 w-4" /> : <CheckSquare className="mr-2 h-4 w-4" />}
                            {allVisibleSelected ? "Clear all" : "Select all"}
                        </Button>
                        <span className="text-sm text-neutral-400">
                            {selectedProjects.length} selected
                        </span>
                    </>
                )}
            </div>

            {selectionMode && selectedProjects.length > 0 && (
                <div className="hidden md:flex flex-wrap items-center gap-2 rounded-lg border border-neutral-800 bg-neutral-950 p-3">
                    {view === "active" ? (
                        <Button
                            onClick={handleBulkArchive}
                            className="bg-amber-600 hover:bg-amber-500 text-white"
                            disabled={bulkBusy}
                        >
                            <Archive className="mr-2 h-4 w-4" />
                            Archive selected
                        </Button>
                    ) : (
                        <Button
                            onClick={handleBulkUnarchive}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white"
                            disabled={bulkBusy}
                        >
                            <ArchiveRestore className="mr-2 h-4 w-4" />
                            Restore selected
                        </Button>
                    )}
                    <Button
                        onClick={handleBulkDelete}
                        variant="destructive"
                        disabled={bulkBusy}
                    >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete selected
                    </Button>
                    {bulkBusy && bulkProgress && (
                        <span className="text-sm text-neutral-400">
                            Deleting {bulkProgress.done}/{bulkProgress.total}
                        </span>
                    )}
                </div>
            )}

            <ProjectList
                projects={visibleProjects}
                onNewProject={handleCreateProject}
                showCreateCard={view === "active" && !selectionMode}
                emptyTitle={view === "active" ? "No presentations yet" : "No archived projects"}
                emptyDescription={view === "active" ? "Create your first AI-powered presentation." : "Archive a project from the card menu to see it here."}
                selectionMode={selectionMode}
                selectedIds={selectedIds}
                onToggleSelect={toggleProjectSelection}
            />

            {selectionMode && selectedProjects.length > 0 && (
                <div className="fixed bottom-4 left-4 right-4 z-50 flex items-center justify-between gap-2 rounded-xl border border-neutral-800 bg-neutral-950/95 p-3 shadow-2xl backdrop-blur md:hidden">
                    {view === "active" ? (
                        <Button
                            onClick={handleBulkArchive}
                            className="flex-1 bg-amber-600 hover:bg-amber-500 text-white"
                            disabled={bulkBusy}
                        >
                            <Archive className="mr-2 h-4 w-4" />
                            Archive
                        </Button>
                    ) : (
                        <Button
                            onClick={handleBulkUnarchive}
                            className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white"
                            disabled={bulkBusy}
                        >
                            <ArchiveRestore className="mr-2 h-4 w-4" />
                            Restore
                        </Button>
                    )}
                    <Button
                        onClick={handleBulkDelete}
                        variant="destructive"
                        className="flex-1"
                        disabled={bulkBusy}
                    >
                        <Trash2 className="mr-2 h-4 w-4" />
                        Delete
                    </Button>
                </div>
            )}

            {bulkBusy && bulkProgress && (
                <div className="fixed bottom-24 left-1/2 z-50 -translate-x-1/2 rounded-full border border-neutral-800 bg-neutral-950/95 px-3 py-1 text-xs text-neutral-300 shadow-lg md:hidden">
                    Deleting {bulkProgress.done}/{bulkProgress.total}
                </div>
            )}
        </div>
    );
}

