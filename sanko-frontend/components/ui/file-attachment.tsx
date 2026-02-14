"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { File as FileIcon, X, Loader2, Check, AlertCircle, Database } from "lucide-react";
import { cn } from "@/lib/utils";

// File status types
type FileStatus = 'hashing' | 'uploading' | 'checking' | 'processing' | 'ready' | 'cached' | 'error';

export interface AttachedFile {
    id: string;
    file: File;
    hash?: string;
    status: FileStatus;
    error?: string;
    r2Key?: string;
    sectionsCount?: number;
    cacheHitType?: "exact" | "similar";
    canonicalHash?: string;
}

interface FileAttachmentBarProps {
    files: AttachedFile[];
    onRemove: (id: string) => void;
    disabled?: boolean;
    className?: string;
}

const statusConfig: Record<FileStatus, { icon: React.ReactNode; color: string; label: string }> = {
    hashing: {
        icon: <Loader2 className="h-3 w-3 animate-spin" />,
        color: "text-blue-400",
        label: "Preparing...",
    },
    uploading: {
        icon: <Loader2 className="h-3 w-3 animate-spin" />,
        color: "text-amber-400",
        label: "Uploading...",
    },
    checking: {
        icon: <Loader2 className="h-3 w-3 animate-spin" />,
        color: "text-purple-400",
        label: "Checking...",
    },
    processing: {
        icon: <Loader2 className="h-3 w-3 animate-spin" />,
        color: "text-orange-400",
        label: "Processing...",
    },
    ready: {
        icon: <Check className="h-3 w-3" />,
        color: "text-emerald-400",
        label: "Ready",
    },
    cached: {
        icon: <Database className="h-3 w-3" />,
        color: "text-cyan-400",
        label: "Cached",
    },
    error: {
        icon: <AlertCircle className="h-3 w-3" />,
        color: "text-red-400",
        label: "Error",
    },
};

export function FileAttachmentBar({ files, onRemove, disabled = false, className }: FileAttachmentBarProps) {
    if (files.length === 0) return null;

    return (
        <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className={cn("mb-3 flex flex-wrap gap-2 overflow-hidden", className)}
        >
            <AnimatePresence mode="popLayout">
                {files.map((file) => {
                    const config = statusConfig[file.status];
                    const isProcessing = ['hashing', 'uploading', 'checking', 'processing'].includes(file.status);
                    const cacheLabel =
                        file.status === "cached" && file.cacheHitType === "similar"
                            ? "Matched"
                            : config.label;

                    return (
                        <motion.div
                            key={file.id}
                            layout
                            initial={{ opacity: 0, scale: 0.8 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.8, transition: { duration: 0.15 } }}
                            className={cn(
                                "group flex items-center gap-2 rounded-lg px-3 py-2 text-xs border transition-all",
                                file.status === 'error'
                                    ? "bg-red-500/10 border-red-500/30 text-red-300"
                                    : file.status === 'cached'
                                        ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-300"
                                        : file.status === 'ready'
                                            ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-300"
                                            : "bg-neutral-900 border-neutral-800 text-neutral-300"
                            )}
                        >
                            {/* File Icon */}
                            <FileIcon className="h-3.5 w-3.5 text-neutral-400 shrink-0" />

                            {/* Filename */}
                            <span className="max-w-[150px] truncate font-medium">
                                {file.file.name}
                            </span>

                            {/* Status */}
                            <span className={cn("flex items-center gap-1 text-[10px]", config.color)}>
                                {config.icon}
                                <span title={file.status === "cached" && file.cacheHitType === "similar" ? "Near-duplicate match: using previously processed document." : undefined}>
                                    {cacheLabel}
                                </span>
                                {file.status === 'cached' && file.sectionsCount && (
                                    <span className="opacity-70">({file.sectionsCount})</span>
                                )}
                            </span>

                            {/* Error message tooltip */}
                            {file.status === 'error' && file.error && (
                                <span className="text-[10px] text-red-400 max-w-[100px] truncate" title={file.error}>
                                    {file.error}
                                </span>
                            )}

                            {/* Remove button - only show if not processing and not disabled */}
                            {!isProcessing && !disabled && (
                                <button
                                    onClick={() => onRemove(file.id)}
                                    className={cn(
                                        "ml-1 rounded-full p-0.5 transition-colors",
                                        "opacity-0 group-hover:opacity-100",
                                        "hover:bg-neutral-800 text-neutral-500 hover:text-white"
                                    )}
                                >
                                    <X className="h-3 w-3" />
                                </button>
                            )}
                        </motion.div>
                    );
                })}
            </AnimatePresence>
        </motion.div>
    );
}

// Helper hook for managing file uploads
export function useFileUpload() {
    const [files, setFiles] = useState<AttachedFile[]>([]);
    const [isUploading, setIsUploading] = useState(false);
    const pollingMapRef = useRef<Map<string, { timerId: ReturnType<typeof setTimeout> | null; controller: AbortController | null }>>(new Map());

    const stopPolling = useCallback((fileId: string) => {
        const tracking = pollingMapRef.current.get(fileId);
        if (!tracking) return;

        if (tracking.timerId) {
            clearTimeout(tracking.timerId);
        }
        if (tracking.controller) {
            tracking.controller.abort();
        }
        pollingMapRef.current.delete(fileId);
    }, []);

    const schedulePoll = useCallback((fileId: string, callback: () => void, delayMs: number) => {
        const tracking = pollingMapRef.current.get(fileId);
        if (!tracking) return;

        if (tracking.timerId) {
            clearTimeout(tracking.timerId);
        }

        tracking.timerId = setTimeout(callback, delayMs);
        pollingMapRef.current.set(fileId, tracking);
    }, []);

    // Compute SHA-256 hash client-side
    const computeHash = async (file: File): Promise<string> => {
        const buffer = await file.arrayBuffer();
        const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
        const hashArray = Array.from(new Uint8Array(hashBuffer));
        return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
    };

    // Check for duplicate by hash
    const isDuplicate = useCallback((hash: string): boolean => {
        return files.some(f => f.hash === hash);
    }, [files]);

    // Add files and start upload
    const addFiles = useCallback(async (newFiles: File[]) => {
        const parseCacheHitType = (uploadedFile: Record<string, unknown>): { hit?: "exact" | "similar"; canonicalHash?: string } => {
            const canonicalHash =
                typeof uploadedFile.canonical_hash === "string"
                    ? uploadedFile.canonical_hash
                    : typeof uploadedFile.canonicalHash === "string"
                        ? uploadedFile.canonicalHash
                        : undefined;

            const rawType =
                typeof uploadedFile.cache_hit_type === "string"
                    ? uploadedFile.cache_hit_type
                    : typeof uploadedFile.match_type === "string"
                        ? uploadedFile.match_type
                        : typeof uploadedFile.dedup_type === "string"
                            ? uploadedFile.dedup_type
                            : undefined;

            const normalized = (rawType ?? "").toLowerCase();
            if (normalized.includes("similar") || normalized.includes("near")) return { hit: "similar", canonicalHash };
            if (normalized.includes("exact")) return { hit: "exact", canonicalHash };

            if (uploadedFile.cached === true) return { hit: "exact", canonicalHash };
            if (uploadedFile.matched === true) return { hit: "similar", canonicalHash };

            return { canonicalHash };
        };

        const pollProcessingStatus = async (fileId: string, fileHash: string) => {
            const maxAttempts = 120;  // 10 minutes max (5s intervals)
            let attempts = 0;
            const requestTimeoutMs = 10000;

            pollingMapRef.current.set(fileId, { timerId: null, controller: null });

            const poll = async () => {
                const currentTracking = pollingMapRef.current.get(fileId);
                if (!currentTracking) return;

                const controller = new AbortController();
                currentTracking.controller = controller;
                pollingMapRef.current.set(fileId, currentTracking);
                const timeoutId = setTimeout(() => controller.abort(), requestTimeoutMs);

                try {
                    const response = await fetch(`/api/generate/processing-status/${fileHash}`, {
                        signal: controller.signal,
                    });

                    clearTimeout(timeoutId);
                    if (controller.signal.aborted) return;

                    if (!response.ok) {
                        if (attempts > 5) {
                            // After 5 failed attempts, assume error
                            stopPolling(fileId);
                            setFiles(prev => prev.map(f =>
                                f.id === fileId ? { ...f, status: 'error', error: 'Status check failed' } : f
                            ));
                            return;
                        }
                        attempts++;
                        schedulePoll(fileId, poll, 5000);
                        return;
                    }

                    const data = await response.json();
                    if (controller.signal.aborted) return;

                    if (data.status === 'completed') {
                        stopPolling(fileId);
                        setFiles(prev => prev.map(f =>
                            f.id === fileId ? {
                                ...f,
                                status: 'cached',
                                sectionsCount: data.sections_count,
                                cacheHitType: data.match_type === "similar" ? "similar" : f.cacheHitType,
                                canonicalHash: typeof data.canonical_hash === "string" ? data.canonical_hash : f.canonicalHash,
                            } : f
                        ));
                    } else if (data.status === 'failed') {
                        stopPolling(fileId);
                        setFiles(prev => prev.map(f =>
                            f.id === fileId ? {
                                ...f,
                                status: 'error',
                                error: data.error_message || 'Processing failed',
                            } : f
                        ));
                    } else if (data.status === 'processing' || data.status === 'queued') {
                        // Still processing, poll again
                        attempts++;
                        if (attempts < maxAttempts) {
                            schedulePoll(fileId, poll, 5000);  // Poll every 5 seconds
                        } else {
                            stopPolling(fileId);
                            setFiles(prev => prev.map(f =>
                                f.id === fileId ? { ...f, status: 'error', error: 'Processing timeout' } : f
                            ));
                        }
                    }
                } catch {
                    clearTimeout(timeoutId);
                    if (controller.signal.aborted) return;
                    attempts++;
                    if (attempts < maxAttempts) {
                        schedulePoll(fileId, poll, 5000);
                    } else {
                        stopPolling(fileId);
                    }
                }
            };

            // Start polling after a short delay
            schedulePoll(fileId, poll, 2000);
        };

        for (const file of newFiles) {
            // Validate file type
            if (!file.type.includes('pdf') && !file.name.toLowerCase().endsWith('.pdf')) {
                const id = crypto.randomUUID();
                setFiles(prev => [...prev, {
                    id,
                    file,
                    status: 'error',
                    error: 'Unsupported file type. Only PDF files are accepted.',
                }]);
                continue;
            }

            // Validate size (20MB)
            if (file.size > 20 * 1024 * 1024) {
                const id = crypto.randomUUID();
                setFiles(prev => [...prev, {
                    id,
                    file,
                    status: 'error',
                    error: 'File exceeds 20MB limit',
                }]);
                continue;
            }

            const id = crypto.randomUUID();

            // Add file in hashing state
            setFiles(prev => [...prev, { id, file, status: 'hashing' }]);

            try {
                // Compute hash
                const hash = await computeHash(file);

                // Check for duplicate
                if (isDuplicate(hash)) {
                    setFiles(prev => prev.filter(f => f.id !== id));
                    // Could show toast here: "File already attached"
                    continue;
                }

                // Update status to uploading
                setFiles(prev => prev.map(f =>
                    f.id === id ? { ...f, hash, status: 'uploading' } : f
                ));

                setIsUploading(true);

                // Upload to backend
                const formData = new FormData();
                formData.append('files', file);

                const response = await fetch('/api/generate/upload', {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Upload failed');
                }

                const data = await response.json();
                const uploadedFile = data.files[0];
                const parsed = parseCacheHitType(uploadedFile);

                if (uploadedFile.cached) {
                    // Already processed - immediately ready
                    setFiles(prev => prev.map(f =>
                        f.id === id ? {
                            ...f,
                            status: 'cached',
                            r2Key: uploadedFile.r2_key,
                            sectionsCount: uploadedFile.sections_count,
                            cacheHitType: parsed.hit ?? "exact",
                            canonicalHash: parsed.canonicalHash,
                        } : f
                    ));
                } else if (parsed.hit === "similar") {
                    // Near-duplicate match - treat as cached to avoid reprocessing.
                    setFiles(prev => prev.map(f =>
                        f.id === id ? {
                            ...f,
                            status: 'cached',
                            r2Key: uploadedFile.r2_key,
                            sectionsCount: uploadedFile.sections_count,
                            cacheHitType: "similar",
                            canonicalHash: parsed.canonicalHash,
                        } : f
                    ));
                } else {
                    // Not cached - background processing started, poll for status
                    setFiles(prev => prev.map(f =>
                        f.id === id ? {
                            ...f,
                            status: 'processing',
                            r2Key: uploadedFile.r2_key,
                        } : f
                    ));

                    // Start polling for processing status
                    pollProcessingStatus(id, hash);
                }

            } catch (error) {
                setFiles(prev => prev.map(f =>
                    f.id === id ? {
                        ...f,
                        status: 'error',
                        error: error instanceof Error ? error.message : 'Upload failed',
                    } : f
                ));
            } finally {
                setIsUploading(false);
            }
        }
    }, [isDuplicate, schedulePoll, stopPolling]);

    // Remove file
    const removeFile = useCallback((id: string) => {
        stopPolling(id);
        setFiles(prev => prev.filter(f => f.id !== id));
    }, [stopPolling]);

    // Get file hashes ready for sending
    const getReadyHashes = useCallback((): string[] => {
        return files
            .filter(f => (f.status === 'ready' || f.status === 'cached') && f.hash)
            .map(f => f.hash!);
    }, [files]);

    // Check if all files are ready
    const allReady = useCallback((): boolean => {
        if (files.length === 0) return true;
        return files.every(f => f.status === 'ready' || f.status === 'cached' || f.status === 'error');
    }, [files]);

    const getFileSummary = useCallback(() => {
        const included = files.filter(f => (f.status === 'ready' || f.status === 'cached') && f.hash).length;
        const excluded = files.filter(f => f.status === 'error').length;
        const processing = files.filter(f => ['hashing', 'uploading', 'checking', 'processing'].includes(f.status)).length;
        return { included, excluded, processing, total: files.length };
    }, [files]);

    // Clear all files (after message sent)
    const clearFiles = useCallback(() => {
        for (const [fileId] of pollingMapRef.current) {
            stopPolling(fileId);
        }
        setFiles([]);
    }, [stopPolling]);

    useEffect(() => {
        const pollingMap = pollingMapRef.current;
        return () => {
            for (const [, tracking] of pollingMap) {
                if (tracking.timerId) {
                    clearTimeout(tracking.timerId);
                }
                if (tracking.controller) {
                    tracking.controller.abort();
                }
            }
            pollingMap.clear();
        };
    }, []);

    return {
        files,
        addFiles,
        removeFile,
        getReadyHashes,
        allReady,
        getFileSummary,
        clearFiles,
        isUploading,
    };
}
