"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Upload, FileText, Check,
    ChevronRight, Loader2, Sparkles, Lock, ArrowLeft
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/auth-provider";
import { ChoiceQuestionCard, ChoiceOption } from "./choice-question-card";
import { FileAttachmentBar, useFileUpload } from "@/components/ui/file-attachment";
import { Id, useCreateRun, useUpdateProject, useRunBySession, useUpdateRun } from "@/hooks/convex";

// Wizard phases
type WizardPhase = "upload" | "scope" | "settings" | "summary";

const SETUP_AUDIENCE_OPTIONS: ChoiceOption[] = [
    { id: "classmates", label: "Classmates", description: "Peer-level class presentations" },
    { id: "class_instructor", label: "Class + instructor", description: "Students plus lecturer/supervisor" },
    { id: "technical", label: "Technical audience", description: "Discipline experts and researchers" },
    { id: "general", label: "General audience", description: "Non-specialist listeners" },
];

const SETUP_SLIDE_RANGE_OPTIONS: ChoiceOption[] = [
    { id: "6-8", label: "6-8 slides", description: "Fast and focused" },
    { id: "8-10", label: "8-10 slides", description: "Balanced detail" },
    { id: "10-12", label: "10-12 slides", description: "Deeper coverage" },
    { id: "auto", label: "Based on structure", description: "Recommended: estimated from your outline inputs" },
];

function parseSlideRangeToCount(range: string | undefined, sectionCount: number): number {
    if (!range || range === "auto") {
        if (sectionCount <= 2) return 8;
        if (sectionCount <= 5) return 10;
        return 12;
    }
    const match = range.match(/^(\d+)\s*-\s*(\d+)$/);
    if (!match) return 10;
    const low = Number(match[1]);
    const high = Number(match[2]);
    if (!Number.isFinite(low) || !Number.isFinite(high) || low <= 0 || high < low) return 10;
    return Math.round((low + high) / 2);
}

function inferFocusAreas(topic: string, existing: string[]): string[] {
    if (existing.length > 0) return existing;
    const normalizedTopic = topic.trim();
    if (!normalizedTopic) return ["Core concepts"];
    const split = normalizedTopic
        .split(/,|;| and /gi)
        .map((part) => part.trim())
        .filter((part) => part.length >= 3);
    if (split.length > 0) return split.slice(0, 5);
    return [normalizedTopic];
}

function toAudienceLabel(value: string | undefined): string {
    const normalized = (value || "").trim().toLowerCase();
    if (normalized === "classmates") return "Classmates";
    if (normalized === "class_instructor") return "Class + instructor";
    if (normalized === "students") return "University students";
    if (normalized === "mixed_academic") return "Mixed academic audience";
    if (normalized === "technical") return "Technical audience";
    if (normalized === "general") return "General audience";
    return value?.trim() || "Classmates";
}

interface UniversityDefaults {
    citationStyle: string;
    spelling: string;
    referencePlacement: string;
    universityShortName: string;
}

interface WizardClarifierProps {
    projectId: string;
    mode: string;
    onComplete: (sessionId: string) => void;
    initialSessionId?: string | null;
}

interface Section {
    id: string;
    title: string;
    preview: string;
}

interface DocumentSectionsItem {
    file_hash: string;
    filename?: string | null;
    status: string;
    sections_count?: number | null;
    sections?: Array<{ title: string; preview: string; page_range?: string; visuals_count?: number }> | null;
    error_message?: string | null;
}

interface DocumentScope {
    fileHash: string;
    filename: string;
    status: "completed" | "queued" | "processing" | "failed" | "missing";
    sectionsCount?: number;
    sections: Section[];
    error?: string;
}

interface CollectedData {
    topic?: string;
    audience?: string;
    slideCount?: number;
    slideRange?: string;
    style?: string;
    sections?: string[];
    sections_by_document?: Record<string, string[]>;
    [key: string]: unknown;
}

type LastAction = "start" | "confirm" | null;

export function WizardClarifier({ projectId, mode, onComplete, initialSessionId = null }: WizardClarifierProps) {
    const { user } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);
    const createRun = useCreateRun();
    const updateProject = useUpdateProject();
    const updateRun = useUpdateRun();

    // Wizard state
    const [phase, setPhase] = useState<WizardPhase>("upload");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [lastAction, setLastAction] = useState<LastAction>(null);

    // Data collection
    const [topic, setTopic] = useState("");
    const [collectedData, setCollectedData] = useState<CollectedData>({});
    const [documents, setDocuments] = useState<DocumentScope[]>([]);
    const [openDocumentHash, setOpenDocumentHash] = useState<string | null>(null);
    const [selectedSectionKeys, setSelectedSectionKeys] = useState<Set<string>>(new Set());

    // University defaults (would come from user profile)
    const [universityDefaults, setUniversityDefaults] = useState<UniversityDefaults | null>(null);

    // File upload
    const {
        files: attachedFiles,
        addFiles,
        removeFile,
        getReadyHashes,
        getFileSummary
    } = useFileUpload();

    // Check if we have a PDF attached
    const hasPdf = attachedFiles.some((f) => f.file.type === "application/pdf");
    const fileSummary = getFileSummary();

    const run = useRunBySession(sessionId || null);
    const persistTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
    const hydratedRef = useRef(false);
    const [linkedFileHashes, setLinkedFileHashes] = useState<string[]>([]);

    const getEffectiveFileHashes = useCallback(() => {
        const hashes = new Set<string>();
        for (const h of linkedFileHashes) hashes.add(h);
        for (const h of getReadyHashes()) hashes.add(h);
        return Array.from(hashes);
    }, [linkedFileHashes, getReadyHashes]);

    const effectiveFileHashes = useMemo(() => getEffectiveFileHashes(), [getEffectiveFileHashes]);
    const hasAnyPdf = hasPdf || effectiveFileHashes.length > 0;

    const refreshDocumentSections = async (fileHashes: string[]) => {
        if (fileHashes.length === 0) {
            setDocuments([]);
            setOpenDocumentHash(null);
            return [] as DocumentScope[];
        }

        try {
            const token = await user?.getIdToken();
            const res = await fetch("/api/generate/document-sections", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    ...(token ? { Authorization: `Bearer ${token}` } : {}),
                },
                body: JSON.stringify({ file_hashes: fileHashes }),
            });

            if (!res.ok) {
                const errText = await res.text().catch(() => "");
                console.error("document-sections failed:", res.status, errText);
                return [] as DocumentScope[];
            }

            const data = await res.json().catch(() => ({}));
            const rawDocs = Array.isArray(data.documents) ? (data.documents as DocumentSectionsItem[]) : [];

            const mapped = rawDocs.map((d): DocumentScope => {
                const statusRaw = (d.status || "missing").toLowerCase();
                const status = (["completed", "queued", "processing", "failed", "missing"].includes(statusRaw) ? statusRaw : "missing") as DocumentScope["status"];
                const filenameFromBackend = typeof d.filename === "string" && d.filename.trim() ? d.filename.trim() : "";
                const localFile = attachedFiles.find((f) => f.hash === d.file_hash);
                const filename = filenameFromBackend || localFile?.file.name || "Document";

                const sections = Array.isArray(d.sections)
                    ? d.sections.map((s, idx) => ({
                        id: `${d.file_hash}::${idx + 1}`,
                        title: String(s.title ?? `Section ${idx + 1}`),
                        preview: String(s.preview ?? ""),
                    }))
                    : [];

                return {
                    fileHash: d.file_hash,
                    filename,
                    status,
                    sectionsCount: typeof d.sections_count === "number" ? d.sections_count : undefined,
                    sections,
                    error: typeof d.error_message === "string" ? d.error_message : undefined,
                };
            });

            setDocuments(mapped);
            setOpenDocumentHash((prev) => {
                if (prev && mapped.some((m) => m.fileHash === prev)) return prev;
                return mapped.find((m) => m.status === "completed")?.fileHash ?? mapped[0]?.fileHash ?? null;
            });
            return mapped;
        } catch (e) {
            console.error("Failed to fetch document sections:", e);
            return [] as DocumentScope[];
        }
    };

    // Initialize session and fetch university defaults
    useEffect(() => {
        async function init() {
            if (!user || sessionId) return;

            try {
                const token = await user.getIdToken();

                // Fetch university context if available
                const profileRes = await fetch("/api/user/profile", {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (profileRes.ok) {
                    const profile = await profileRes.json();
                    if (profile.universityId) {
                        setUniversityDefaults({
                            citationStyle: profile.citationStyle || "harvard",
                            spelling: profile.spellingVariant || "british",
                            referencePlacement: profile.referencePlacement || "last_slide",
                            universityShortName: profile.universityShortName || "University"
                        });
                    }
                }
            } catch (e) {
                console.error("Failed to fetch user profile:", e);
            }
        }

        init();
    }, [user, sessionId]);

    useEffect(() => {
        if (!initialSessionId) return;
        if (sessionId === initialSessionId) return;
        hydratedRef.current = false;
        setSessionId(initialSessionId);
        setPhase("settings");
        setError(null);
    }, [initialSessionId, sessionId]);

    useEffect(() => {
        if (!run || hydratedRef.current) return;
        hydratedRef.current = true;

        const brief = (run.brief as Record<string, unknown> | undefined) ?? undefined;
        if (brief) {
            const savedTopic = typeof brief.topic === "string" ? brief.topic : "";
            const savedPhase = typeof brief.phase === "string" ? (brief.phase as WizardPhase) : null;
            const savedCollected = typeof brief.collectedData === "object" && brief.collectedData ? (brief.collectedData as CollectedData) : null;

            if (!topic && savedTopic) setTopic(savedTopic);
            if (Object.keys(collectedData).length === 0 && savedCollected) setCollectedData(savedCollected);
            // Only set phase if we haven't moved forward yet.
            if ((phase === "upload" || phase === "settings") && savedPhase && ["upload", "scope", "settings", "summary"].includes(savedPhase)) {
                setPhase(savedPhase);
            }
        }

        const uploads = (run.uploads as Record<string, unknown> | undefined) ?? undefined;
        if (uploads && Array.isArray(uploads.file_hashes)) {
            const hashes = (uploads.file_hashes as unknown[]).map(String).filter(Boolean);
            if (hashes.length > 0) setLinkedFileHashes(hashes);
        }

        const scope = (run.scope as Record<string, unknown> | undefined) ?? undefined;
        if (scope && typeof scope.sections_by_document === "object" && scope.sections_by_document) {
            const byDoc = scope.sections_by_document as Record<string, unknown>;
            const next = new Set<string>();
            for (const [hash, titlesRaw] of Object.entries(byDoc)) {
                if (!Array.isArray(titlesRaw)) continue;
                for (const t of titlesRaw) {
                    const title = String(t || "").trim();
                    if (title) next.add(`${hash}::${title}`);
                }
            }
            if (next.size > 0) setSelectedSectionKeys(next);
        }
    }, [run, topic, collectedData, phase]);

    // If we resume into scope without local File objects, load section previews from cached hashes.
    useEffect(() => {
        if (phase !== "scope") return;
        if (documents.length > 0) return;
        if (effectiveFileHashes.length === 0) return;
        void refreshDocumentSections(effectiveFileHashes);
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [phase, documents.length, effectiveFileHashes.join(",")]);

    // Persist wizard state to run (debounced).
    useEffect(() => {
        if (!run?._id) return;
        if (persistTimerRef.current) clearTimeout(persistTimerRef.current);

        persistTimerRef.current = setTimeout(() => {
            void updateRun({
                id: run._id,
                brief: {
                    topic,
                    phase,
                    collectedData,
                },
                uploads: {
                    file_hashes: getEffectiveFileHashes(),
                },
            });
        }, 500);

        return () => {
            if (persistTimerRef.current) clearTimeout(persistTimerRef.current);
        };
    }, [run?._id, topic, phase, collectedData, updateRun, getEffectiveFileHashes]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            addFiles(Array.from(e.target.files));
            e.target.value = '';
        }
    };

    const startSession = async () => {
        const fileHashes = getEffectiveFileHashes();
        // Topic is optional if we have at least one processed/cached PDF.
        if (!user || (!topic.trim() && fileHashes.length === 0)) return;

        setIsLoading(true);
        setError(null);
        setLastAction("start");

        try {
            const token = await user.getIdToken();

            const res = await fetch("/api/generate/start", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    project_id: projectId,
                    mode: mode,
                    topic: topic.trim() ? topic : undefined,
                    file_hashes: fileHashes.length > 0 ? fileHashes : undefined,
                })
            });

            if (res.ok) {
                const data = await res.json();
                setSessionId(data.session_id);

                // Persist run + bind it as active (best effort, should not block UX).
                try {
                    const runId = await createRun({
                        projectId: projectId as Id<"projects">,
                        sessionId: data.session_id,
                        mode,
                        stage: "clarifying",
                        brief: { ...collectedData, topic: topic.trim() ? topic : undefined },
                        uploads: {
                            file_hashes: fileHashes,
                            files: attachedFiles.map((f) => ({
                                name: f.file.name,
                                size: f.file.size,
                                type: f.file.type,
                                hash: f.hash,
                                status: f.status,
                            })),
                        },
                    });
                    await updateProject({
                        id: projectId as Id<"projects">,
                        activeRunId: runId as Id<"generationRuns">,
                        sessionId: data.session_id, // legacy sync
                    });
                } catch (e) {
                    console.error("Failed to persist run history:", e);
                }

                // If we have any ready/cached PDFs (including from prior runs), always show section scope.
                if (hasAnyPdf) {
                    const allHashes = getEffectiveFileHashes();
                    const mappedDocs = await refreshDocumentSections(allHashes);
                    // Default: preselect all sections in completed docs (or fallback to "full document" if none).
                    const nextSelected = new Set<string>();
                    for (const doc of mappedDocs) {
                        if (doc.status !== "completed") continue;
                        for (const section of doc.sections) {
                            nextSelected.add(`${doc.fileHash}::${section.title}`);
                        }
                    }
                    setSelectedSectionKeys(nextSelected);
                    setPhase("scope");
                } else if (data.complete || data.needs_confirmation || data.next_step === "summary") {
                    setPhase("summary");
                } else {
                    setPhase("settings");
                }
            } else {
                const err = await res.json();
                setError(err.detail || "Failed to start session");
            }
        } catch (e) {
            console.error("Error starting session:", e);
            setError("Failed to connect. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    const buildWizardPayload = (): CollectedData => {
        const selectedSections = Array.isArray(collectedData.sections)
            ? collectedData.sections.filter((s) => typeof s === "string" && s.trim())
            : [];
        const focusAreas = inferFocusAreas(topic, selectedSections);
        const slideRange = typeof collectedData.slideRange === "string" ? collectedData.slideRange : "auto";
        const slideCount = typeof collectedData.slideCount === "number"
            ? collectedData.slideCount
            : parseSlideRangeToCount(slideRange, focusAreas.length);

        return {
            ...collectedData,
            topic: topic.trim() ? topic.trim() : undefined,
            audience: toAudienceLabel(collectedData.audience),
            slideRange,
            slideCount,
            sections: focusAreas,
            focus_areas: focusAreas,
            style: "detailed",
            emphasis_style: "detailed",
        };
    };

    const handleConfirm = async () => {
        if (!sessionId) return;

        setIsLoading(true);
        setError(null);
        setLastAction("confirm");

        try {
            const token = await user?.getIdToken();
            const res = await fetch("/api/generate/confirm", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    wizard_data: buildWizardPayload(),
                    source: "wizard_setup_v2",
                })
            });

            if (res.ok) {
                onComplete(sessionId);
            } else {
                const err = await res.json().catch(() => ({}));
                setError(err.detail || "Failed to confirm. Please try again.");
            }
        } catch (e) {
            console.error("Error confirming:", e);
            setError("Failed to confirm. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    // Progress bar calculation
    const getProgress = () => {
        const phases: WizardPhase[] = ["upload", "scope", "settings", "summary"];
        return ((phases.indexOf(phase) + 1) / phases.length) * 100;
    };

    const goBack = () => {
        if (phase === "scope") setPhase("upload");
        else if (phase === "settings") setPhase(hasAnyPdf ? "scope" : "upload");
        else if (phase === "summary") setPhase("settings");
    };

    const retryLastAction = async () => {
        if (lastAction === "start") {
            await startSession();
            return;
        }
        if (lastAction === "confirm") {
            await handleConfirm();
        }
    };

    return (
        <div className="flex h-full flex-col bg-neutral-950">
            {/* Progress Bar */}
            <div className="px-4 py-3 border-b border-neutral-800/50">
                <div className="flex items-center gap-2 mb-2">
                    {["upload", "scope", "settings", "summary"].map((p, i) => (
                        <div
                            key={p}
                            className={cn(
                                "flex-1 h-1 rounded-full transition-colors",
                                i <= ["upload", "scope", "settings", "summary"].indexOf(phase)
                                    ? "bg-emerald-500"
                                    : "bg-neutral-800"
                            )}
                        />
                    ))}
                </div>
                <div className="flex items-center justify-between text-xs">
                    <span className="text-neutral-500 uppercase tracking-wider font-medium">
                        {phase === "upload" && "Getting Started"}
                        {phase === "scope" && "Document Sections"}
                        {phase === "settings" && "Setup"}
                        {phase === "summary" && "Review & Confirm"}
                    </span>
                    <span className="text-emerald-500 font-mono" title="Wizard step estimate">
                        ~{Math.round(getProgress())}%
                    </span>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-dark" aria-busy={isLoading}>
                {phase !== "upload" && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={goBack}
                        disabled={isLoading}
                        className="h-8 text-neutral-400 hover:text-white hover:bg-neutral-900/50"
                    >
                        <ArrowLeft className="mr-2 h-4 w-4" />
                        Back
                    </Button>
                )}

                <AnimatePresence mode="wait">
                    {/* Upload Phase */}
                    {phase === "upload" && (
                        <motion.div
                            key="upload"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="space-y-6"
                        >
                            {/* Topic Input */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-neutral-300">
                                    What is your presentation about?
                                </label>
                                <Input
                                    value={topic}
                                    onChange={(e) => setTopic(e.target.value)}
                                    placeholder="e.g., Climate Change Solutions, Machine Learning Applications..."
                                    className="bg-neutral-900/50 border-neutral-800 text-white placeholder:text-neutral-600 focus:border-emerald-500/50"
                                />
                            </div>

                            {/* PDF Upload Area */}
                            <div className="space-y-2">
                                <label className="text-sm font-medium text-neutral-300 flex items-center gap-2">
                                    <FileText className="h-4 w-4" />
                                    Upload a document (optional)
                                </label>

                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    className="hidden"
                                    accept=".pdf"
                                    onChange={handleFileSelect}
                                />

                                {attachedFiles.length === 0 ? (
                                    <button
                                        onClick={() => fileInputRef.current?.click()}
                                        className={cn(
                                            "w-full border-2 border-dashed rounded-xl p-8 transition-all",
                                            "border-neutral-800 hover:border-emerald-500/50 hover:bg-emerald-500/5",
                                            "flex flex-col items-center gap-3 text-center"
                                        )}
                                    >
                                        <Upload className="h-8 w-8 text-neutral-600" />
                                        <div>
                                            <p className="text-sm font-medium text-neutral-400">
                                                Drop PDF here or click to upload
                                            </p>
                                            <p className="text-xs text-neutral-600 mt-1">
                                                We&apos;ll extract sections for you to choose from
                                            </p>
                                        </div>
                                    </button>
                                ) : (
                                    <FileAttachmentBar
                                        files={attachedFiles}
                                        onRemove={removeFile}
                                        disabled={isLoading}
                                    />
                                )}
                            </div>

                            {/* University Defaults Badge */}
                            {universityDefaults && (
                                <div className="rounded-lg bg-emerald-500/5 border border-emerald-500/20 p-4">
                                    <div className="flex items-center gap-2 mb-2">
                                        <Lock className="h-4 w-4 text-emerald-500" />
                                        <span className="text-sm font-medium text-emerald-400">
                                            Auto-applied from {universityDefaults.universityShortName}
                                        </span>
                                    </div>
                                    <div className="grid grid-cols-2 gap-2 text-xs">
                                        <div className="flex justify-between">
                                            <span className="text-neutral-500">Citation:</span>
                                            <span className="text-neutral-300">{universityDefaults.citationStyle}</span>
                                        </div>
                                        <div className="flex justify-between">
                                            <span className="text-neutral-500">Spelling:</span>
                                            <span className="text-neutral-300">{universityDefaults.spelling}</span>
                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Continue Button */}
                            <Button
                                onClick={startSession}
                                disabled={(!topic.trim() && effectiveFileHashes.length === 0) || isLoading}
                                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white h-12"
                            >
                                {isLoading ? (
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                    <ChevronRight className="h-4 w-4 mr-2" />
                                )}
                                {fileSummary.processing > 0 && fileSummary.included > 0
                                    ? `Continue (${fileSummary.included} ready, ${fileSummary.processing} processing)`
                                    : fileSummary.processing > 0 && fileSummary.included === 0 && hasPdf
                                        ? "Processing PDF..."
                                        : `Continue${fileSummary.included > 0 ? ` (${fileSummary.included} file${fileSummary.included > 1 ? "s" : ""} included)` : ""}`}
                            </Button>
                            {!hasPdf && linkedFileHashes.length > 0 && (
                                <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-3 text-xs text-neutral-400">
                                    Using {linkedFileHashes.length} cached document(s) from your last run. Click Continue to start from them.
                                </div>
                            )}
                            {attachedFiles.length > 0 && (
                                <div className="rounded-lg border border-neutral-800 bg-neutral-900/40 p-3 text-xs text-neutral-400">
                                    <p>
                                        Included: {fileSummary.included} | Excluded: {fileSummary.excluded}
                                        {fileSummary.processing > 0 ? ` | Processing: ${fileSummary.processing}` : ""}
                                    </p>
                                    {fileSummary.excluded > 0 && (
                                        <p className="mt-1 text-amber-300">
                                            Generation will continue without excluded files.
                                        </p>
                                    )}
                                </div>
                            )}
                        </motion.div>
                    )}

                    {/* Scope Phase (Section Selection) */}
                    {phase === "scope" && (
                        <motion.div
                            key="scope"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="space-y-4"
                        >
                            <div className="flex items-center gap-2 mb-4">
                                <FileText className="h-5 w-5 text-emerald-500" />
                                <h3 className="text-lg font-medium text-white">
                                    Choose what to include
                                </h3>
                            </div>
                            <p className="text-sm text-neutral-400">
                                Select sections per PDF. Collapsed PDFs save space, and you can expand others anytime.
                            </p>

                            <div className="flex items-center justify-between gap-2">
                                <Button
                                    variant="outline"
                                    className="border-neutral-800 text-neutral-200"
                                    onClick={() => {
                                        void refreshDocumentSections(getEffectiveFileHashes());
                                    }}
                                >
                                    Refresh
                                </Button>
                                <div className="text-xs text-neutral-500">
                                    Selected: <span className="text-neutral-200">{selectedSectionKeys.size}</span>
                                </div>
                            </div>

                            <div className="space-y-2">
                                {documents.map((doc) => {
                                    const isOpen = openDocumentHash === doc.fileHash;
                                    const statusLabel =
                                        doc.status === "completed" ? "Ready" :
                                            doc.status === "processing" ? "Processing" :
                                                doc.status === "queued" ? "Queued" :
                                                    doc.status === "failed" ? "Failed" : "Missing";

                                    return (
                                        <div key={doc.fileHash} className="rounded-lg border border-neutral-800 bg-neutral-900/30 overflow-hidden">
                                            <button
                                                type="button"
                                                className="w-full px-4 py-3 flex items-center justify-between hover:bg-neutral-900/40 transition-colors"
                                                onClick={() => setOpenDocumentHash((prev) => (prev === doc.fileHash ? null : doc.fileHash))}
                                            >
                                                <div className="min-w-0 text-left">
                                                    <div className="truncate text-sm font-medium text-white">{doc.filename}</div>
                                                    <div className="text-[11px] text-neutral-500">
                                                        {doc.sectionsCount !== undefined ? `${doc.sectionsCount} sections` : "Sections unknown"}
                                                    </div>
                                                </div>
                                                <div className={cn(
                                                    "shrink-0 rounded-full border px-2 py-0.5 text-[10px]",
                                                    doc.status === "completed"
                                                        ? "border-emerald-500/20 bg-emerald-500/10 text-emerald-300"
                                                        : doc.status === "failed"
                                                            ? "border-red-500/20 bg-red-500/10 text-red-200"
                                                            : "border-neutral-800 bg-neutral-950/30 text-neutral-300"
                                                )}>
                                                    {statusLabel}
                                                </div>
                                            </button>

                                            {isOpen && (
                                                <div className="px-4 pb-4">
                                                    {doc.error && (
                                                        <div className="mb-3 rounded-md border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-200">
                                                            {doc.error}
                                                        </div>
                                                    )}

                                                    {doc.status !== "completed" ? (
                                                        <div className="text-xs text-neutral-500">
                                                            This PDF is not ready yet. Once processing finishes, hit Refresh.
                                                        </div>
                                                    ) : (
                                                        <>
                                                            <div className="mb-3 flex items-center justify-between">
                                                                <div className="text-xs text-neutral-500">Sections</div>
                                                                <Button
                                                                    variant="outline"
                                                                    size="sm"
                                                                    className="h-7 border-neutral-800 text-neutral-200"
                                                                    onClick={() => {
                                                                        setSelectedSectionKeys((prev) => {
                                                                            const next = new Set(prev);
                                                                            for (const s of doc.sections) {
                                                                                next.add(`${doc.fileHash}::${s.title}`);
                                                                            }
                                                                            return next;
                                                                        });
                                                                    }}
                                                                >
                                                                    Select all
                                                                </Button>
                                                            </div>

                                                            <div className="space-y-2">
                                                                {doc.sections.map((section) => {
                                                                    const key = `${doc.fileHash}::${section.title}`;
                                                                    const selected = selectedSectionKeys.has(key);
                                                                    return (
                                                                        <button
                                                                            key={key}
                                                                            aria-pressed={selected}
                                                                            aria-label={`Toggle section ${section.title}`}
                                                                            onClick={() => {
                                                                                setSelectedSectionKeys((prev) => {
                                                                                    const next = new Set(prev);
                                                                                    if (next.has(key)) next.delete(key);
                                                                                    else next.add(key);
                                                                                    return next;
                                                                                });
                                                                            }}
                                                                            className={cn(
                                                                                "w-full text-left rounded-lg border p-3 transition-all",
                                                                                selected
                                                                                    ? "border-emerald-500 bg-emerald-500/10"
                                                                                    : "border-neutral-800 bg-neutral-900/30 hover:border-neutral-700"
                                                                            )}
                                                                        >
                                                                            <div className="flex items-start gap-3">
                                                                                <div className={cn(
                                                                                    "mt-1 h-5 w-5 rounded border-2 flex items-center justify-center",
                                                                                    selected
                                                                                        ? "border-emerald-500 bg-emerald-500"
                                                                                        : "border-neutral-700"
                                                                                )}>
                                                                                    {selected && <Check className="h-3 w-3 text-white" />}
                                                                                </div>
                                                                                <div>
                                                                                    <p className="font-medium text-white">{section.title}</p>
                                                                                    <p className="text-xs text-neutral-500 mt-1 line-clamp-2">
                                                                                        {section.preview}
                                                                                    </p>
                                                                                </div>
                                                                            </div>
                                                                        </button>
                                                                    );
                                                                })}
                                                            </div>
                                                        </>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>

                            <div className="flex gap-3 pt-4">
                                <Button
                                    variant="outline"
                                    onClick={() => setSelectedSectionKeys(new Set())}
                                    className="flex-1"
                                >
                                    Clear
                                </Button>
                                <Button
                                    onClick={() => {
                                        // Flatten selected section titles for backend (current backend expects titles).
                                        const byDoc: Record<string, string[]> = {};
                                        for (const key of selectedSectionKeys) {
                                            const sep = "::";
                                            const idx = key.indexOf(sep);
                                            const hash = idx >= 0 ? key.slice(0, idx) : "";
                                            const title = idx >= 0 ? key.slice(idx + sep.length) : "";
                                            if (!hash || !title) continue;
                                            if (!byDoc[hash]) byDoc[hash] = [];
                                            byDoc[hash].push(title);
                                        }
                                        const flatTitles = Object.values(byDoc).flat();

                                        const nextCollected: CollectedData = {
                                            ...collectedData,
                                            sections_by_document: byDoc,
                                            sections: flatTitles,
                                        };
                                        setCollectedData(nextCollected);

                                        if (run?._id) {
                                            void updateRun({
                                                id: run._id,
                                                scope: { sections_by_document: byDoc, sections: flatTitles },
                                                brief: { ...nextCollected, topic: topic.trim() ? topic : undefined, sections: flatTitles },
                                            });
                                        }
                                        setPhase("settings");
                                    }}
                                    disabled={selectedSectionKeys.size === 0}
                                    className="flex-1 bg-emerald-600 hover:bg-emerald-500"
                                >
                                    Continue with {selectedSectionKeys.size}
                                    <ChevronRight className="h-4 w-4 ml-2" />
                                </Button>
                            </div>
                        </motion.div>
                    )}

                    {/* Settings Phase */}
                    {phase === "settings" && (
                        <motion.div
                            key="settings"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="space-y-6"
                        >
                            <ChoiceQuestionCard
                                question="How long should the deck be?"
                                options={SETUP_SLIDE_RANGE_OPTIONS}
                                onSelect={(id) => {
                                    const sectionCount = Array.isArray(collectedData.sections) ? collectedData.sections.length : 0;
                                    setCollectedData(prev => ({
                                        ...prev,
                                        slideRange: id,
                                        slideCount: parseSlideRangeToCount(id, sectionCount),
                                    }));
                                }}
                                showCustomInput={false}
                                isLoading={isLoading}
                            />

                            {collectedData.slideRange && (
                                <ChoiceQuestionCard
                                    question="Who will this be presented to?"
                                    options={SETUP_AUDIENCE_OPTIONS}
                                    onSelect={(id) => {
                                        setCollectedData(prev => ({ ...prev, audience: id }));
                                    }}
                                    showCustomInput={false}
                                    isLoading={isLoading}
                                />
                            )}

                            <div className="rounded-lg border border-neutral-800 bg-neutral-900/30 p-4 text-xs text-neutral-400">
                                Next step is outline review. You can edit structure directly and use prompts to fine-tune before generation.
                            </div>

                            <Button
                                disabled={!collectedData.audience || !collectedData.slideRange || isLoading}
                                onClick={() => {
                                    const selectedSections = Array.isArray(collectedData.sections)
                                        ? collectedData.sections.filter((s) => typeof s === "string" && s.trim())
                                        : [];
                                    const focusAreas = inferFocusAreas(topic, selectedSections);
                                    const slideRange = typeof collectedData.slideRange === "string" ? collectedData.slideRange : "auto";
                                    const nextCollected: CollectedData = {
                                        ...collectedData,
                                        audience: toAudienceLabel(collectedData.audience),
                                        slideRange,
                                        slideCount: parseSlideRangeToCount(slideRange, focusAreas.length),
                                        sections: focusAreas,
                                        focus_areas: focusAreas,
                                        style: "detailed",
                                        emphasis_style: "detailed",
                                    };
                                    setCollectedData(nextCollected);
                                    setPhase("summary");
                                }}
                                className="w-full bg-emerald-600 hover:bg-emerald-500"
                            >
                                Review setup
                                <ChevronRight className="ml-2 h-4 w-4" />
                            </Button>
                        </motion.div>
                    )}

                    {/* Summary Phase */}
                    {phase === "summary" && (
                        <motion.div
                            key="summary"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="space-y-4"
                        >
                            <div className="flex items-center gap-2 mb-4">
                                <Sparkles className="h-5 w-5 text-emerald-500" />
                                <h3 className="text-lg font-medium text-white">
                                    Ready to generate!
                                </h3>
                            </div>

                            {/* Summary Card */}
                            <div className="rounded-lg bg-neutral-900/50 border border-neutral-800 p-4 space-y-3">
                                <div className="flex justify-between text-sm">
                                    <span className="text-neutral-500">Topic</span>
                                    <span className="text-white">{topic}</span>
                                </div>
                                {collectedData.audience && (
                                    <div className="flex justify-between text-sm">
                                        <span className="text-neutral-500">Audience</span>
                                        <span className="text-white capitalize">{collectedData.audience}</span>
                                    </div>
                                )}
                                {collectedData.slideCount && (
                                    <div className="flex justify-between text-sm">
                                        <span className="text-neutral-500">Deck length</span>
                                        <span className="text-white">
                                            {typeof collectedData.slideRange === "string" && collectedData.slideRange !== "auto"
                                                ? `${collectedData.slideRange} (target ${collectedData.slideCount})`
                                                : `Based on structure (target ${collectedData.slideCount})`}
                                        </span>
                                    </div>
                                )}
                                {Array.isArray(collectedData.sections) && collectedData.sections.length > 0 && (
                                    <div className="flex justify-between text-sm">
                                        <span className="text-neutral-500">Outline focus</span>
                                        <span className="text-white">{collectedData.sections.length} section(s)</span>
                                    </div>
                                )}
                                {universityDefaults && (
                                    <>
                                        <hr className="border-neutral-800" />
                                        <div className="flex justify-between text-sm">
                                            <span className="text-neutral-500">Citation</span>
                                            <span className="text-emerald-400 flex items-center gap-1">
                                                <Lock className="h-3 w-3" />
                                                {universityDefaults.citationStyle}
                                            </span>
                                        </div>
                                    </>
                                )}
                            </div>

                            {/* Confirm Button */}
                            <Button
                                onClick={handleConfirm}
                                disabled={isLoading}
                                className="w-full bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white h-12 text-lg font-semibold shadow-lg shadow-emerald-900/30"
                            >
                                {isLoading ? (
                                    <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                                ) : (
                                    <Sparkles className="h-5 w-5 mr-2" />
                                )}
                                Generate Presentation
                            </Button>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Error Display */}
                {error && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-300"
                        role="alert"
                        aria-live="polite"
                    >
                        <p>{error}</p>
                        <div className="mt-3 flex gap-2">
                            {lastAction && (
                                <Button
                                    size="sm"
                                    variant="outline"
                                    className="border-red-500/40 bg-transparent text-red-100"
                                    onClick={retryLastAction}
                                    disabled={isLoading}
                                >
                                    Retry
                                </Button>
                            )}
                            {phase !== "upload" && (
                                <Button
                                    size="sm"
                                    variant="ghost"
                                    className="text-neutral-300 hover:text-white hover:bg-neutral-800"
                                    onClick={goBack}
                                    disabled={isLoading}
                                >
                                    Back
                                </Button>
                            )}
                        </div>
                    </motion.div>
                )}
            </div>
        </div>
    );
}
