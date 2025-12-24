"use client";

import { motion } from "framer-motion";
import { MoreVertical, FileText, Download, Trash, Edit } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { formatDistanceToNow } from "date-fns";
import { cn } from "@/lib/utils";

interface ProjectCardProps {
    project: {
        id: string;
        title: string;
        updatedAt: Date | string;
        slidesCount?: number;
        thumbnailUrl?: string; // Placeholder for now
        status: string;
    };
}

export function ProjectCard({ project }: ProjectCardProps) {
    return (
        <motion.div
            whileHover={{ y: -4, scale: 1.02 }}
            className="group relative flex flex-col justify-between rounded-xl border border-neutral-800/80 bg-neutral-900 p-4 shadow-md shadow-black/40 transition-all hover:border-emerald-500/50 hover:shadow-[0_4px_30px_-10px_rgba(16,185,129,0.3)] overflow-hidden"
        >
            {/* Subtle emerald gradient glow on hover */}
            <div className="absolute inset-0 bg-gradient-to-br from-emerald-500/5 to-transparent opacity-0 transition-opacity duration-500 group-hover:opacity-100 pointer-events-none" />

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
                            : "bg-neutral-800 text-neutral-400 border-neutral-700"
                    )}>
                        {project.status === "completed" ? "Ready" : project.status.charAt(0).toUpperCase() + project.status.slice(1)}
                    </span>
                </div>
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0 text-neutral-400 hover:text-white hover:bg-neutral-800 transition-colors">
                            <span className="sr-only">Open menu</span>
                            <MoreVertical className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuItem>
                            <Edit className="mr-2 h-4 w-4" /> Edit
                        </DropdownMenuItem>
                        <DropdownMenuItem>
                            <Download className="mr-2 h-4 w-4" /> Download
                        </DropdownMenuItem>
                        <DropdownMenuItem className="text-red-600 focus:text-red-500">
                            <Trash className="mr-2 h-4 w-4" /> Delete
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            </div>
        </motion.div>
    );
}
