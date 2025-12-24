"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ChevronLeft, Terminal, AlertCircle, Search } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";

interface SessionLog {
    role: string;
    content: string;
    timestamp?: string;
    initial_prompt?: string;
    raw_response?: string;
}

interface SessionData {
    interaction_id: string;
    state: string;
    mode: string;
    topic?: string;
    clarification_count: number;
    history?: SessionLog[];
    error?: string;
}

export function SessionHistory() {
    const [sessions, setSessions] = useState<SessionData[]>([]);
    const [selectedSession, setSelectedSession] = useState<SessionData | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchSessions() {
            try {
                const res = await fetch("/api/generate/sessions");
                if (res.ok) {
                    const data = await res.json();
                    setSessions(data);
                }
            } catch (e) {
                console.error("Failed to fetch sessions", e);
            } finally {
                setLoading(false);
            }
        }
        fetchSessions();
    }, []);

    if (loading) {
        return <div className="p-8 text-neutral-400">Loading history...</div>;
    }

    return (
        <div className="flex h-screen bg-black text-neutral-200 font-sans">
            {/* Sidebar: Session List */}
            <div className="w-1/3 border-r border-neutral-800 flex flex-col bg-neutral-950">
                <div className="p-4 border-b border-neutral-800 flex items-center justify-between">
                    <h2 className="font-semibold text-white flex items-center gap-2">
                        <Terminal className="w-4 h-4 text-emerald-500" /> Recent Sessions
                    </h2>
                    <Link href="/playground">
                        <Button variant="ghost" size="sm" className="h-7 text-xs text-neutral-400">
                            Back to Playground
                        </Button>
                    </Link>
                </div>
                <div className="flex-1 overflow-y-auto p-2 space-y-2">
                    {sessions.map((session, idx) => (
                        <div
                            key={idx}
                            onClick={() => setSelectedSession(session)}
                            className={cn(
                                "p-3 rounded-lg border cursor-pointer transition-all",
                                selectedSession === session
                                    ? "bg-emerald-900/20 border-emerald-500/50"
                                    : "bg-neutral-900/50 border-neutral-800 hover:border-neutral-700"
                            )}
                        >
                            <div className="flex justify-between items-start mb-1">
                                <span className="text-sm font-medium text-white truncate max-w-[200px]">
                                    {session.topic || "Untitled Session"}
                                </span>
                                <span className={cn(
                                    "text-[10px] px-1.5 py-0.5 rounded capitalize",
                                    session.state === "completed" ? "bg-emerald-500/20 text-emerald-400" :
                                        session.state === "failed" ? "bg-red-500/20 text-red-400" :
                                            "bg-blue-500/20 text-blue-400"
                                )}>
                                    {session.state}
                                </span>
                            </div>
                            <div className="flex justify-between text-[11px] text-neutral-500 font-mono">
                                <span>{session.mode}</span>
                                <span>{session.history?.length || 0} msgs</span>
                            </div>
                        </div>
                    ))}
                    {sessions.length === 0 && (
                        <div className="text-center p-8 text-neutral-500 text-sm">No sessions found.</div>
                    )}
                </div>
            </div>

            {/* Main Area: Interaction Log */}
            <div className="w-2/3 flex flex-col bg-neutral-950/50">
                {selectedSession ? (
                    <>
                        <div className="p-4 border-b border-neutral-800 bg-neutral-950">
                            <h3 className="font-semibold text-white">{selectedSession.topic || "Details"}</h3>
                            <div className="flex gap-4 mt-2 text-xs text-neutral-400 font-mono">
                                <span>ID: {selectedSession.interaction_id?.slice(0, 12)}...</span>
                                <span>Mode: {selectedSession.mode}</span>
                            </div>
                        </div>
                        <div className="flex-1 overflow-y-auto p-6 space-y-6">
                            {selectedSession.history?.map((log, i) => (
                                <div key={i} className="space-y-2">
                                    <div className="flex items-center gap-2">
                                        <span className={cn(
                                            "text-xs font-bold uppercase tracking-wider px-2 py-1 rounded",
                                            log.role === "user" ? "bg-blue-500/20 text-blue-400" :
                                                log.role === "assistant" ? "bg-emerald-500/20 text-emerald-400" :
                                                    "bg-neutral-700 text-neutral-300"
                                        )}>
                                            {log.role}
                                        </span>
                                        {log.timestamp && <span className="text-[10px] text-neutral-600 font-mono">{log.timestamp}</span>}
                                    </div>
                                    <div className="pl-2 border-l-2 border-neutral-800 ml-2">
                                        <div className="bg-neutral-900 rounded p-3 text-sm text-neutral-300 leading-relaxed whitespace-pre-wrap font-mono">
                                            {log.content}
                                            {log.initial_prompt && (
                                                <div className="mt-2 pt-2 border-t border-neutral-800 text-xs text-neutral-500">
                                                    <div className="font-bold mb-1">INITIAL PROMPT:</div>
                                                    {log.initial_prompt}
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            {!selectedSession.history && (
                                <div className="text-neutral-500">No logs available for this session.</div>
                            )}
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-neutral-500 gap-4">
                        <Terminal className="w-12 h-12 opacity-20" />
                        <p>Select a session to view the interaction log.</p>
                    </div>
                )}
            </div>
        </div>
    );
}
