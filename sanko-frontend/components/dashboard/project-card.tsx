"use client";

import { motion } from "framer-motion";
import { MoreVertical, FileText, Trash, Edit3, Archive, ArchiveRestore, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { Id, useDeleteProject, useUpdateProject } from "@/hooks/convex";
import { useToast } from "@/components/ui/toast";

interface ProjectCardProps {
    project: {
        id: string;
        title: string;
        updatedAt: Date | string;
        slidesCount?: number;
        thumbnailUrl?: string; // Placeholder for now
        status: string;
        archiveSourceStatus?: string;
    };
    selectionMode?: boolean;
    selected?: boolean;
    onToggleSelect?: () => void;
}

export function ProjectCard({
    project,
    selectionMode = false,
    selected = false,
    onToggleSelect,
}: ProjectCardProps) {
    const router = useRouter();
    const { toast } = useToast();
    const projectId = project.id as Id<"projects">;
    const updateProject = useUpdateProject();
    const deleteProject = useDeleteProject();
    const [renaming, setRenaming] = useState(false);
    const [titleDraft, setTitleDraft] = useState(project.title);
    const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
    const [isMutating, setIsMutating] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const isArchived = project.status === "archived";
    const isGenerating = project.status === "generating";

    const trimmedTitle = useMemo(() => titleDraft.replace(/\s+/g, " ").trim(), [titleDraft]);
    const canSaveRename = trimmedTitle.length > 0 && trimmedTitle !== project.title && !isMutating;
    const restoreStatus = project.archiveSourceStatus || "draft";

    const runAction = async (action: () => Promise<void>) => {
        if (isMutating) return;
        setIsMutating(true);
        try {
            await action();
        } catch (error) {
            console.error("Project action failed:", error);
        } finally {
            setIsMutating(false);
        }
    };

    const handleDelete = async () => {
        if (isDeleting || isMutating) return;
        setConfirmDeleteOpen(false);
        setIsDeleting(true);
        try {
            await deleteProject({ id: projectId });
            toast({
                title: "Project deleted",
                description: `"${project.title}" was deleted.`,
                variant: "success",
            });
        } catch (error) {
            console.error("Project delete failed:", error);
            toast({
                title: "Delete failed",
                description: `Could not delete "${project.title}". Please try again.`,
                variant: "error",
            });
            setIsDeleting(false);
        }
    };

    if (isDeleting) {
        return (
            <motion.div
                initial={{ opacity: 0.7 }}
                animate={{ opacity: [0.7, 0.45, 0.7] }}
                transition={{ duration: 1.1, repeat: Infinity }}
                className="relative flex min-h-[260px] flex-col justify-center rounded-xl border border-neutral-800/80 bg-neutral-900 p-4"
            >
                <div className="text-center text-sm text-neutral-400">Deleting project...</div>
            </motion.div>
        );
    }

    const handleCardActivate = () => {
        if (selectionMode && onToggleSelect) {
            onToggleSelect();
            return;
        }
        router.push(`/editor/${project.id}`);
    };

    return (
        <>
            <motion.div
                whileHover={{ y: -4, scale: 1.02 }}
                onClick={handleCardActivate}
                onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        handleCardActivate();
                    }
                }}
                role="button"
                tabIndex={0}
                className="group relative flex flex-col justify-between rounded-xl border border-neutral-800/80 bg-neutral-900 p-4 shadow-md shadow-black/40 transition-all hover:border-emerald-500/50 hover:shadow-[0_4px_30px_-10px_rgba(16,185,129,0.3)] overflow-hidden"
            >
                {/* Subtle emerald gradient glow on hover */}
                <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100 pointer-events-none" />
                {selectionMode && (
                    <button
                        type="button"
                        onClick={(e) => {
                            e.stopPropagation();
                            onToggleSelect?.();
                        }}
                        className={cn(
                            "absolute left-3 top-3 z-20 inline-flex h-6 w-6 items-center justify-center rounded border",
                            selected
                                ? "border-emerald-500 bg-emerald-500 text-white"
                                : "border-neutral-600 bg-neutral-900 text-transparent hover:border-emerald-500/70"
                        )}
                        aria-label={selected ? "Unselect project" : "Select project"}
                    >
                        <Check className="h-3.5 w-3.5" />
                    </button>
                )}

                <div className="flex flex-col space-y-4 relative z-10">
                    {/* Thumbnail Placeholder */}
                    <div className="relative aspect-video w-full overflow-hidden rounded-lg bg-neutral-900 border border-neutral-800 group-hover:border-neutral-700 transition-colors">
                        {project.thumbnailUrl ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={project.thumbnailUrl} alt={project.title} className="object-cover w-full h-full opacity-80 group-hover:opacity-100 transition-opacity" />
                        ) : (
                            <div className="flex h-full w-full items-center justify-center text-neutral-700 group-hover:text-emerald-500/50 transition-colors">
                                <FileText className="h-10 w-10" />
                            </div>
                        )}
                    </div>

                    <div className="space-y-1.5">
                        <h3 className="font-semibold text-white group-hover:text-emerald-400 transition-colors leading-tight">
                            {project.title}
                        </h3>
                        <p className="text-xs text-neutral-400 group-hover:text-neutral-300 transition-colors font-medium">
                            Edited {formatDistanceToNow(new Date(project.updatedAt), { addSuffix: true })}
                        </p>
                    </div>
                </div>

                <div className="flex items-center justify-between pt-4 relative z-10">
                    <div className="flex items-center space-x-2">
                        <span className={cn(
                            "inline-flex items-center rounded-md px-2 py-1 text-xs font-medium border",
                            project.status === "completed"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : project.status === "archived"
                                    ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                                    : "bg-neutral-800 text-neutral-400 border-neutral-700"
                        )}>
                            {project.status === "completed" ? "Ready" : project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                        </span>
                    </div>
                    <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                            <Button
                                variant="ghost"
                                className="h-8 w-8 p-0 text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors"
                                onClick={(e) => e.stopPropagation()}
                            >
                                <span className="sr-only">Open menu</span>
                                <MoreVertical className="h-4 w-4" />
                            </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                            <DropdownMenuItem onSelect={() => router.push(`/editor/${project.id}`)}>
                                <Edit3 className="mr-2 h-4 w-4" /> Open
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                disabled={isMutating}
                                onSelect={() => {
                                    setTitleDraft(project.title);
                                    setRenaming(true);
                                }}
                            >
                                <Edit3 className="mr-2 h-4 w-4" /> Rename
                            </DropdownMenuItem>
                            <DropdownMenuItem
                                disabled={isGenerating || isMutating}
                                onSelect={() => runAction(async () => {
                                    if (isArchived) {
                                        await updateProject({
                                            id: projectId,
                                            status: restoreStatus,
                                            clearArchiveSourceStatus: true,
                                        });
                                    } else {
                                        await updateProject({
                                            id: projectId,
                                            status: "archived",
                                            archiveSourceStatus: project.status,
                                        });
                                    }
                                })}
                            >
                                {isArchived ? (
                                    <ArchiveRestore className="mr-2 h-4 w-4" />
                                ) : (
                                    <Archive className="mr-2 h-4 w-4" />
                                )}
                                {isArchived ? "Unarchive" : "Archive"}
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            <DropdownMenuItem
                                variant="destructive"
                                disabled={isGenerating || isMutating}
                                onSelect={() => setConfirmDeleteOpen(true)}
                            >
                                <Trash className="mr-2 h-4 w-4" /> Delete
                            </DropdownMenuItem>
                        </DropdownMenuContent>
                    </DropdownMenu>
                </div>
            </motion.div>

            <Dialog open={renaming} onOpenChange={setRenaming}>
                <DialogContent className="bg-neutral-950 border border-neutral-800 text-white">
                    <DialogHeader>
                        <DialogTitle>Rename project</DialogTitle>
                        <DialogDescription className="text-neutral-400">
                            Update the project title shown on your dashboard and editor.
                        </DialogDescription>
                    </DialogHeader>
                    <Input
                        value={titleDraft}
                        onChange={(e) => setTitleDraft(e.target.value)}
                        maxLength={120}
                        className="bg-neutral-900 border-neutral-700 text-white"
                    />
                    <DialogFooter>
                        <Button
                            variant="outline"
                            onClick={() => setRenaming(false)}
                            className="border-neutral-700 text-neutral-200"
                        >
                            Cancel
                        </Button>
                        <Button
                            disabled={!canSaveRename}
                            onClick={() => runAction(async () => {
                                await updateProject({
                                    id: projectId,
                                    title: trimmedTitle,
                                });
                                setRenaming(false);
                            })}
                            className="bg-emerald-600 hover:bg-emerald-500 text-white"
                        >
                            Save
                        </Button>
                    </DialogFooter>
                </DialogContent>
            </Dialog>

            <AlertDialog open={confirmDeleteOpen} onOpenChange={setConfirmDeleteOpen}>
                <AlertDialogContent className="bg-neutral-950 border border-neutral-800 text-white">
                    <AlertDialogHeader>
                        <AlertDialogTitle>Delete project?</AlertDialogTitle>
                        <AlertDialogDescription className="text-neutral-400">
                            This permanently deletes &quot;{project.title}&quot; and cannot be undone.
                        </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                        <AlertDialogCancel className="border-neutral-700 text-neutral-200">Cancel</AlertDialogCancel>
                        <AlertDialogAction
                            variant="destructive"
                            onClick={handleDelete}
                        >
                            Delete
                        </AlertDialogAction>
                    </AlertDialogFooter>
                </AlertDialogContent>
            </AlertDialog>
        </>
    );
}
