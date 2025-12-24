"use client";

import { useState, useEffect } from "react";
import { ClarifierChat } from "./clarifier-chat";
import { BlueprintReview } from "./blueprint-review";
import { GenerationProgress } from "./generation-progress";
import { SlideViewer } from "./slide-viewer";
import { EditorLayout } from "./editor-layout";
import { useAuth } from "@/components/auth-provider";
import { Loader2 } from "lucide-react";

type EditorStage = "clarifying" | "blueprint" | "generating" | "completed";

interface EditorWorkspaceProps {
    projectId: string;
}

export function EditorWorkspace({ projectId }: EditorWorkspaceProps) {
    const { user } = useAuth();
    const [stage, setStage] = useState<EditorStage>("clarifying");
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [projectMode, setProjectMode] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchProject() {
            if (!user || !projectId) return;

            try {
                const token = await user.getIdToken();
                const res = await fetch(`/api/projects/${projectId}`, {
                    headers: { Authorization: `Bearer ${token}` }
                });

                if (res.ok) {
                    const data = await res.json();
                    setProjectMode(data.project.mode);
                } else {
                    console.error("Failed to fetch project");
                }
            } catch (error) {
                console.error("Error fetching project:", error);
            } finally {
                setLoading(false);
            }
        }

        fetchProject();
    }, [user, projectId]);

    if (loading) {
        return (
            <div className="flex h-screen w-full items-center justify-center bg-black text-emerald-500">
                <Loader2 className="h-8 w-8 animate-spin" />
            </div>
        );
    }

    // Passed to ClarifierChat to trigger state change
    const onClarificationComplete = (sid: string) => {
        setSessionId(sid);
        setStage("blueprint");
    };

    // Passed to BlueprintReview
    const onBlueprintApproved = () => {
        setStage("generating");
    };

    // Passed to GenerationProgress
    const onGenerationComplete = (result: any) => {
        setStage("completed");
        // We might redirect or show the final slide deck here
        console.log("Generation result:", result);
    };

    return (
        <EditorLayout
            sidebar={
                <ClarifierChat
                    projectId={projectId}
                    mode={projectMode || "synthesis"}
                    onOrderComplete={onClarificationComplete}
                    readOnly={stage !== "clarifying"} // Disable chat input after clarification
                />
            }
        >
            {stage === "clarifying" && (
                <div className="flex h-full w-full flex-col items-center justify-center text-center">
                    <div className="max-w-md space-y-4">
                        <h3 className="text-xl font-semibold text-white">Presentation Preview</h3>
                        <p className="text-sm text-neutral-400">
                            The slide deck will appear here once we've composed the blueprint.
                        </p>
                        <div className="mt-6 p-4 rounded-xl border border-dashed border-neutral-800 bg-neutral-900/30">
                            <div className="h-8 w-2/3 bg-neutral-800/50 rounded mb-3 mx-auto" />
                            <div className="h-4 w-full bg-neutral-800/50 rounded mb-2" />
                            <div className="h-4 w-5/6 bg-neutral-800/50 rounded mb-2 mx-auto" />
                        </div>
                    </div>
                </div>
            )}

            {stage === "blueprint" && sessionId && (
                <BlueprintReview sessionId={sessionId} onApprove={onBlueprintApproved} />
            )}

            {stage === "generating" && sessionId && (
                <GenerationProgress sessionId={sessionId} onComplete={onGenerationComplete} />
            )}

            {stage === "completed" && sessionId && (
                <SlideViewer sessionId={sessionId} />
            )}

        </EditorLayout>
    );
}
