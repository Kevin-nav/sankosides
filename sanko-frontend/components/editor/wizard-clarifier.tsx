"use client";

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
    Upload, FileText, Check,
    ChevronRight, Loader2, Sparkles, Lock
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/auth-provider";
import { ChoiceQuestionCard, ChoiceOption } from "./choice-question-card";
import { FileAttachmentBar, useFileUpload } from "@/components/ui/file-attachment";

// Wizard phases
type WizardPhase = "upload" | "scope" | "settings" | "clarify" | "summary";

interface AIQuestion {
    id: string;
    question: string;
    options: ChoiceOption[];
    fieldKey: string;
    allowCustom: boolean;
    allowMultiple: boolean;
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
}

interface Section {
    id: string;
    title: string;
    preview: string;
}

interface CollectedData {
    topic?: string;
    audience?: string;
    slideCount?: number | "auto";
    style?: string;
    sections?: string[];
    [key: string]: string | number | string[] | undefined;
}

export function WizardClarifier({ projectId, mode, onComplete }: WizardClarifierProps) {
    const { user } = useAuth();
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Wizard state
    const [phase, setPhase] = useState<WizardPhase>("upload");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Data collection
    const [topic, setTopic] = useState("");
    const [collectedData, setCollectedData] = useState<CollectedData>({});
    const [sections, setSections] = useState<Section[]>([]);
    const [selectedSections, setSelectedSections] = useState<Set<string>>(new Set());

    // AI clarification state
    const [currentQuestion, setCurrentQuestion] = useState<AIQuestion | null>(null);
    const [answeredQuestions, setAnsweredQuestions] = useState<{ question: string; answer: string }[]>([]);

    // University defaults (would come from user profile)
    const [universityDefaults, setUniversityDefaults] = useState<UniversityDefaults | null>(null);

    // File upload
    const { files: attachedFiles, addFiles, removeFile, getReadyHashes, allReady } = useFileUpload();

    // Check if we have a PDF attached
    const hasPdf = attachedFiles.some(f => f.file.type === "application/pdf");

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

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files.length > 0) {
            addFiles(Array.from(e.target.files));
            e.target.value = '';
        }
    };

    const startSession = async () => {
        if (!user || !topic.trim()) return;

        setIsLoading(true);
        setError(null);

        try {
            const token = await user.getIdToken();
            const fileHashes = getReadyHashes();

            const res = await fetch("/api/generate/start", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    project_id: projectId,
                    mode: mode,
                    topic: topic,
                    file_hashes: fileHashes.length > 0 ? fileHashes : undefined,
                    wizard_data: collectedData
                })
            });

            if (res.ok) {
                const data = await res.json();
                setSessionId(data.session_id);

                // If PDF was uploaded, sections might be returned
                if (data.sections) {
                    setSections(data.sections);
                    setPhase("scope");
                } else if (mode !== "research") {
                    // Skip to settings for non-research mode without PDF
                    setPhase("settings");
                } else {
                    // For research mode, go straight to clarify
                    setPhase("clarify");
                    if (data.next_question) {
                        setCurrentQuestion(data.next_question);
                    } else {
                        startAIClarification(data.session_id);
                    }
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

    const handleQuestionAnswer = async (answer: string, customText?: string) => {
        if (!currentQuestion || !sessionId) return;

        const finalAnswer = customText || answer;

        // Record the answer
        setAnsweredQuestions(prev => [...prev, {
            question: currentQuestion.question,
            answer: finalAnswer
        }]);

        setCollectedData(prev => ({
            ...prev,
            [currentQuestion.fieldKey]: finalAnswer
        }));

        setIsLoading(true);

        try {
            const token = await user?.getIdToken();
            const fileHashes = getReadyHashes();
            const res = await fetch("/api/generate/clarify/stream", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    answer: finalAnswer,
                    field_key: currentQuestion.fieldKey,
                    file_hashes: fileHashes.length > 0 ? fileHashes : undefined,
                })
            });

            if (!res.ok) throw new Error("Failed to submit answer");

            // Process SSE response for next question or completion
            const reader = res.body?.getReader();
            const decoder = new TextDecoder();

            if (reader) {
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const events = buffer.split("\n\n");
                    buffer = events.pop() || "";

                    for (const eventStr of events) {
                        if (!eventStr.trim()) continue;

                        const lines = eventStr.split("\n");
                        let eventType = "";
                        let eventData = "";

                        for (const line of lines) {
                            if (line.startsWith("event: ")) eventType = line.slice(7);
                            else if (line.startsWith("data: ")) eventData = line.slice(6);
                        }

                        if (!eventType || !eventData) continue;

                        try {
                            const data = JSON.parse(eventData);

                            if (eventType === "question") {
                                // New question from AI
                                setCurrentQuestion({
                                    id: data.id,
                                    question: data.question_text,
                                    options: data.suggested_options || [],
                                    fieldKey: data.field_key,
                                    allowCustom: data.allow_custom ?? true,
                                    allowMultiple: data.allow_multiple ?? false
                                });
                            } else if (eventType === "needs_confirmation" || (eventType === "done" && data.complete)) {
                                // All questions answered, show summary
                                setCurrentQuestion(null);
                                setPhase("summary");
                            } else if (eventType === "blueprint_ready") {
                                // Skip to completion
                                onComplete(sessionId);
                            }
                        } catch (parseError) {
                            console.error("Failed to parse SSE data:", parseError);
                        }
                    }
                }
            }
        } catch (e) {
            console.error("Error submitting answer:", e);
            setError("Failed to submit answer. Please try again.");
        } finally {
            setIsLoading(false);
        }
    };

    const handleConfirm = async () => {
        if (!sessionId) return;

        setIsLoading(true);

        try {
            const token = await user?.getIdToken();
            const res = await fetch("/api/generate/confirm", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ session_id: sessionId })
            });

            if (res.ok) {
                onComplete(sessionId);
            } else {
                setError("Failed to confirm. Please try again.");
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
        const phases: WizardPhase[] = ["upload", "scope", "settings", "clarify", "summary"];
        return ((phases.indexOf(phase) + 1) / phases.length) * 100;
    };

    return (
        <div className="flex h-full flex-col bg-neutral-950">
            {/* Progress Bar */}
            <div className="px-4 py-3 border-b border-neutral-800/50">
                <div className="flex items-center gap-2 mb-2">
                    {["upload", "scope", "settings", "clarify", "summary"].map((p, i) => (
                        <div
                            key={p}
                            className={cn(
                                "flex-1 h-1 rounded-full transition-colors",
                                i <= ["upload", "scope", "settings", "clarify", "summary"].indexOf(phase)
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
                        {phase === "settings" && "Quick Settings"}
                        {phase === "clarify" && "Refining Details"}
                        {phase === "summary" && "Review & Confirm"}
                    </span>
                    <span className="text-emerald-500 font-mono">
                        {Math.round(getProgress())}%
                    </span>
                </div>
            </div>

            {/* Main Content Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-dark">
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
                                disabled={!topic.trim() || isLoading || (hasPdf && !allReady())}
                                className="w-full bg-emerald-600 hover:bg-emerald-500 text-white h-12"
                            >
                                {isLoading ? (
                                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                                ) : (
                                    <ChevronRight className="h-4 w-4 mr-2" />
                                )}
                                {hasPdf && !allReady() ? "Processing PDF..." : "Continue"}
                            </Button>
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
                                    We found {sections.length} sections
                                </h3>
                            </div>
                            <p className="text-sm text-neutral-400">
                                Select which sections to include in your presentation:
                            </p>

                            <div className="space-y-2">
                                {sections.map((section) => (
                                    <button
                                        key={section.id}
                                        onClick={() => {
                                            setSelectedSections(prev => {
                                                const next = new Set(prev);
                                                if (next.has(section.id)) {
                                                    next.delete(section.id);
                                                } else {
                                                    next.add(section.id);
                                                }
                                                return next;
                                            });
                                        }}
                                        className={cn(
                                            "w-full text-left rounded-lg border p-4 transition-all",
                                            selectedSections.has(section.id)
                                                ? "border-emerald-500 bg-emerald-500/10"
                                                : "border-neutral-800 bg-neutral-900/50 hover:border-neutral-700"
                                        )}
                                    >
                                        <div className="flex items-start gap-3">
                                            <div className={cn(
                                                "mt-1 h-5 w-5 rounded border-2 flex items-center justify-center",
                                                selectedSections.has(section.id)
                                                    ? "border-emerald-500 bg-emerald-500"
                                                    : "border-neutral-700"
                                            )}>
                                                {selectedSections.has(section.id) && (
                                                    <Check className="h-3 w-3 text-white" />
                                                )}
                                            </div>
                                            <div>
                                                <p className="font-medium text-white">{section.title}</p>
                                                <p className="text-xs text-neutral-500 mt-1 line-clamp-2">
                                                    {section.preview}
                                                </p>
                                            </div>
                                        </div>
                                    </button>
                                ))}
                            </div>

                            <div className="flex gap-3 pt-4">
                                <Button
                                    variant="outline"
                                    onClick={() => setSelectedSections(new Set(sections.map(s => s.id)))}
                                    className="flex-1"
                                >
                                    Select All
                                </Button>
                                <Button
                                    onClick={() => {
                                        setCollectedData(prev => ({
                                            ...prev,
                                            sections: Array.from(selectedSections)
                                        }));
                                        setPhase("settings");
                                    }}
                                    disabled={selectedSections.size === 0}
                                    className="flex-1 bg-emerald-600 hover:bg-emerald-500"
                                >
                                    Continue with {selectedSections.size}
                                    <ChevronRight className="h-4 w-4 ml-2" />
                                </Button>
                            </div>
                        </motion.div>
                    )}

                    {/* Settings Phase (Quick Settings) */}
                    {phase === "settings" && (
                        <motion.div
                            key="settings"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="space-y-6"
                        >
                            {/* Audience Question */}
                            <ChoiceQuestionCard
                                question="Who is the target audience?"
                                options={[
                                    { id: "undergrad", label: "Undergraduates", icon: "🎓", description: "College/university students" },
                                    { id: "graduate", label: "Graduate Level", icon: "🔬", description: "Masters/PhD researchers" },
                                    { id: "industry", label: "Industry Experts", icon: "💼", description: "Working professionals" },
                                    { id: "general", label: "General Audience", icon: "🌍", description: "Non-specialists" },
                                ]}
                                onSelect={(id) => {
                                    setCollectedData(prev => ({ ...prev, audience: id }));
                                }}
                                isLoading={isLoading}
                            />

                            {collectedData.audience && (
                                <>
                                    {/* Slide Count */}
                                    <ChoiceQuestionCard
                                        question="How many slides?"
                                        options={[
                                            { id: "5", label: "5 slides", description: "Brief overview" },
                                            { id: "10", label: "10 slides", description: "Standard length" },
                                            { id: "15", label: "15 slides", description: "Detailed coverage" },
                                            { id: "auto", label: "Let AI decide", icon: "✨", description: "Based on content" },
                                        ]}
                                        onSelect={(id) => {
                                            setCollectedData(prev => ({
                                                ...prev,
                                                slideCount: id === "auto" ? "auto" : parseInt(id)
                                            }));
                                        }}
                                        showCustomInput={true}
                                        isLoading={isLoading}
                                    />
                                </>
                            )}

                            {collectedData.slideCount && (
                                <>
                                    {/* Style */}
                                    <ChoiceQuestionCard
                                        question="Presentation style?"
                                        options={[
                                            { id: "detailed", label: "Detailed", icon: "📊", description: "In-depth with examples" },
                                            { id: "concise", label: "Concise", icon: "⚡", description: "Key points only" },
                                            { id: "visual", label: "Visual Heavy", icon: "🎨", description: "Emphasis on graphics" },
                                        ]}
                                        onSelect={(id) => {
                                            setCollectedData(prev => ({ ...prev, style: id }));
                                            // Move to clarify phase
                                            setPhase("clarify");
                                            // Start AI questions
                                            startAIClarification();
                                        }}
                                        isLoading={isLoading}
                                    />
                                </>
                            )}
                        </motion.div>
                    )}

                    {/* Clarify Phase (AI Questions) */}
                    {phase === "clarify" && (
                        <motion.div
                            key="clarify"
                            initial={{ opacity: 0, x: 20 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -20 }}
                            className="space-y-6"
                        >
                            {/* Answered questions (collapsed) */}
                            {answeredQuestions.length > 0 && (
                                <div className="space-y-2">
                                    {answeredQuestions.map((qa, i) => (
                                        <div key={i} className="flex items-center gap-2 text-xs text-neutral-500">
                                            <Check className="h-3 w-3 text-emerald-500" />
                                            <span className="truncate">{qa.question}</span>
                                            <span className="text-emerald-400 ml-auto">{qa.answer}</span>
                                        </div>
                                    ))}
                                </div>
                            )}

                            {/* Current AI Question */}
                            {currentQuestion && (
                                <ChoiceQuestionCard
                                    question={currentQuestion.question}
                                    options={currentQuestion.options}
                                    onSelect={handleQuestionAnswer}
                                    allowMultiple={currentQuestion.allowMultiple}
                                    showCustomInput={currentQuestion.allowCustom}
                                    isLoading={isLoading}
                                />
                            )}

                            {/* Loading state */}
                            {isLoading && !currentQuestion && (
                                <div className="flex items-center justify-center py-8">
                                    <Loader2 className="h-6 w-6 text-emerald-500 animate-spin" />
                                </div>
                            )}
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
                                        <span className="text-neutral-500">Slides</span>
                                        <span className="text-white">
                                            {collectedData.slideCount === "auto" ? "AI decides" : collectedData.slideCount}
                                        </span>
                                    </div>
                                )}
                                {collectedData.style && (
                                    <div className="flex justify-between text-sm">
                                        <span className="text-neutral-500">Style</span>
                                        <span className="text-white capitalize">{collectedData.style}</span>
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

                            {/* Answered Questions */}
                            {answeredQuestions.length > 0 && (
                                <div className="rounded-lg bg-neutral-900/30 border border-neutral-800/50 p-4">
                                    <p className="text-xs text-neutral-500 mb-2 uppercase tracking-wider">
                                        Additional Details
                                    </p>
                                    <div className="space-y-2">
                                        {answeredQuestions.map((qa, i) => (
                                            <div key={i} className="flex justify-between text-sm">
                                                <span className="text-neutral-500 truncate max-w-[60%]">{qa.question}</span>
                                                <span className="text-white">{qa.answer}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

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
                        className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-400"
                    >
                        {error}
                    </motion.div>
                )}
            </div>
        </div>
    );

    // Helper function to start AI clarification
    async function startAIClarification(overrideSessionId?: string) {
        const activeSessionId = overrideSessionId || sessionId;
        if (!activeSessionId) return;

        setIsLoading(true);

        try {
            const token = await user?.getIdToken();
            const fileHashes = getReadyHashes();
            const res = await fetch("/api/generate/clarify/stream", {
                method: "POST",
                headers: {
                    Authorization: `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: activeSessionId,
                    wizard_data: collectedData,
                    request_next_question: true,
                    file_hashes: fileHashes.length > 0 ? fileHashes : undefined,
                })
            });

            if (!res.ok) throw new Error("Failed to start clarification");

            // Process SSE for first question
            const reader = res.body?.getReader();
            const decoder = new TextDecoder();

            if (reader) {
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const events = buffer.split("\n\n");
                    buffer = events.pop() || "";

                    for (const eventStr of events) {
                        if (!eventStr.trim()) continue;

                        const lines = eventStr.split("\n");
                        let eventType = "";
                        let eventData = "";

                        for (const line of lines) {
                            if (line.startsWith("event: ")) eventType = line.slice(7);
                            else if (line.startsWith("data: ")) eventData = line.slice(6);
                        }

                        if (!eventType || !eventData) continue;

                        try {
                            const data = JSON.parse(eventData);

                            if (eventType === "question") {
                                setCurrentQuestion({
                                    id: data.id,
                                    question: data.question_text,
                                    options: data.suggested_options || [],
                                    fieldKey: data.field_key,
                                    allowCustom: data.allow_custom ?? true,
                                    allowMultiple: data.allow_multiple ?? false
                                });
                            } else if (eventType === "needs_confirmation" || (eventType === "done" && data.complete)) {
                                // No more questions needed, go to summary
                                setCurrentQuestion(null);
                                setPhase("summary");
                            }
                        } catch (parseError) {
                            console.error("Failed to parse SSE:", parseError);
                        }
                    }
                }
            }
        } catch (e) {
            console.error("Error starting AI clarification:", e);
            // Fallback: skip to summary if AI fails
            setPhase("summary");
        } finally {
            setIsLoading(false);
        }
    }
}
