"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Send, Paperclip, Bot, User, File as FileIcon, X, Loader2, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useAuth } from "@/components/auth-provider";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ConfirmationCard } from "./confirmation-card";

interface ChatMessage {
    id: string;
    role: "assistant" | "user";
    content: string;
    thinking?: string; // Observability trace
    attachments?: File[];
}

interface ClarifierChatProps {
    projectId: string;
    mode: string;
    topic?: string;
    onOrderComplete?: (sessionId: string) => void;
    readOnly?: boolean;
    promptOverrides?: Record<string, string>;
    // Observability callbacks
    onAgentChange?: (agent: string | null) => void;
    onThinkingUpdate?: (thinking: string) => void;
}

export function ClarifierChat({ projectId, mode, onOrderComplete, readOnly = false, promptOverrides, topic, onAgentChange, onThinkingUpdate }: ClarifierChatProps) {
    const { user } = useAuth();
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState("");
    const [isTyping, setIsTyping] = useState(true); // Start with typing as we fetch initial
    const [attachments, setAttachments] = useState<File[]>([]);
    const [sessionId, setSessionId] = useState<string | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [isCopied, setIsCopied] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const fileInputRef = useRef<HTMLInputElement>(null);
    const initialized = useRef(false);

    // Confirmation state
    const [pendingConfirmation, setPendingConfirmation] = useState<any>(null);
    const [isConfirming, setIsConfirming] = useState(false);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages, isTyping, error]);

    // Initial Start Call
    useEffect(() => {
        if (initialized.current || !user || !projectId) return;
        initialized.current = true;
        setError(null);

        async function startSession() {
            try {
                const token = await user?.getIdToken();
                const res = await fetch("/api/generate/start", {
                    method: "POST",
                    headers: {
                        "Authorization": `Bearer ${token}`,
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        project_id: projectId,
                        mode: mode,
                        topic: topic,
                        prompt_overrides: promptOverrides
                    })
                });

                if (res.ok) {
                    const data = await res.json();
                    setSessionId(data.session_id);
                    setMessages([{
                        id: "init",
                        role: "assistant", // Changed from "model" to "assistant" to match
                        content: data.clarification_question || "Hello! Let's start building your presentation. What is the topic?"
                    }]);
                } else {
                    const err = await res.json();
                    setError(err.detail || "Failed to start session");
                    console.error("Failed to start session", err);
                }
            } catch (e) {
                console.error("Failed to connect to backend, falling back to DEMO MODE", e);
                // Fallback to Mock Session
                setSessionId("mock-session-" + Date.now());
                setMessages([{
                    id: "init",
                    role: "assistant",
                    content: "⚠️ **DEMO MODE ACTIVE**\n\nBackend connection failed, but you can still test the UI interactions.\n\nHello! I am ready to help you design your presentation. What topic should we explore?"
                }]);
            } finally {
                setIsTyping(false);
            }
        }

        startSession();
    }, [user, projectId, mode, topic]); // promptOverrides is intentionally excluded to avoid restarting on every keypress


    const handleSend = async () => {
        if ((!input.trim() && attachments.length === 0) || isTyping || !sessionId) return;

        const userMsg: ChatMessage = {
            id: Date.now().toString(),
            role: "user",
            content: input,
            attachments: [...attachments],
        };

        setMessages((prev) => [...prev, userMsg]);
        setInput("");
        const currentAttachments = [...attachments];
        setAttachments([]);
        setIsTyping(true);

        if (sessionId?.startsWith("mock-session")) {
            // Mock Response Logic
            setIsTyping(true);
            setTimeout(() => {
                const streamMsgId = Date.now().toString();
                setMessages((prev) => [...prev, {
                    id: streamMsgId,
                    role: "assistant",
                    content: "",
                    thinking: "Analyzing request...\nAccessing neural pathways...\nMocking response for UI testing..."
                }]);

                // Simulate streaming
                let thinking = "Analyzing request...\nAccessing neural pathways...\nMocking response for UI testing...";
                let content = "";
                const fullContent = "This is a **simulated response** to demonstrate the UI.\n\nIn a real session, I would clarify your needs regarding:  \n- **" + input + "**  \n- Target Audience  \n- Visual Style\n\nShall we proceed with the blueprint?";

                let i = 0;
                const interval = setInterval(() => {
                    content += fullContent.charAt(i);
                    setMessages((prev) => prev.map(m =>
                        m.id === streamMsgId
                            ? { ...m, content: content }
                            : m
                    ));
                    onThinkingUpdate?.(thinking + (i % 5 === 0 ? "." : ""));
                    i++;
                    if (i >= fullContent.length) {
                        clearInterval(interval);
                        setIsTyping(false);
                        onThinkingUpdate?.(thinking + "\nDone.");
                    }
                }, 30);
            }, 1000);
            return;
        }

        try {
            const token = await user?.getIdToken();

            // Prepare payload
            let promptText = input;

            for (const file of currentAttachments) {
                if (file.type === "text/plain" || file.name.endsWith(".md")) {
                    const text = await file.text();
                    promptText += `\n\n[Attached File: ${file.name}]\n${text}`;
                }
            }

            // Use streaming endpoint
            const res = await fetch("/api/generate/clarify/stream", {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    session_id: sessionId,
                    answer: promptText
                })
            });

            if (!res.ok) {
                throw new Error("Stream request failed");
            }

            const reader = res.body?.getReader();
            const decoder = new TextDecoder();

            // Create a placeholder message for streaming
            const streamMsgId = Date.now().toString();
            setMessages((prev) => [...prev, {
                id: streamMsgId,
                role: "assistant",
                content: "",
                thinking: ""
            }]);

            // Notify observability: agent is active
            onAgentChange?.("Clarifier (Flash)");
            onThinkingUpdate?.("");

            let accumulatedThinking = "";
            let accumulatedContent = "";

            if (reader) {
                let buffer = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });

                    // Parse SSE events from buffer
                    const events = buffer.split("\n\n");
                    buffer = events.pop() || ""; // Keep incomplete event in buffer

                    for (const eventStr of events) {
                        if (!eventStr.trim()) continue;

                        const lines = eventStr.split("\n");
                        let eventType = "";
                        let eventData = "";

                        for (const line of lines) {
                            if (line.startsWith("event: ")) {
                                eventType = line.slice(7);
                            } else if (line.startsWith("data: ")) {
                                eventData = line.slice(6);
                            }
                        }

                        if (!eventType || !eventData) continue;

                        try {
                            const data = JSON.parse(eventData);

                            if (eventType === "thinking") {
                                accumulatedThinking += data.text || "";
                                setMessages((prev) => prev.map(m =>
                                    m.id === streamMsgId
                                        ? { ...m, thinking: accumulatedThinking }
                                        : m
                                ));
                                // Update observability panel
                                onThinkingUpdate?.(accumulatedThinking);
                            } else if (eventType === "content") {
                                accumulatedContent += data.text || "";
                                setMessages((prev) => prev.map(m =>
                                    m.id === streamMsgId
                                        ? { ...m, content: accumulatedContent }
                                        : m
                                ));
                            } else if (eventType === "done") {
                                // Final update with complete data
                                setMessages((prev) => prev.map(m =>
                                    m.id === streamMsgId
                                        ? { ...m, content: data.content || accumulatedContent, thinking: data.thinking || accumulatedThinking }
                                        : m
                                ));

                                // Clear agent on done
                                onAgentChange?.(null);

                                // Check for blueprint completion
                                // (For full integration, the streaming endpoint would need to signal this)
                            } else if (eventType === "blueprint_ready") {
                                // Blueprint is ready! Trigger handoff
                                onAgentChange?.(null);
                                if (onOrderComplete && sessionId) {
                                    setTimeout(() => {
                                        onOrderComplete(sessionId);
                                    }, 1000);
                                }
                            } else if (eventType === "error") {
                                console.error("Stream error:", data.error);
                            } else if (eventType === "needs_confirmation") {
                                // Show confirmation card
                                setPendingConfirmation({
                                    summary: data.summary,
                                    message: data.message
                                });
                                onAgentChange?.(null);
                            }
                        } catch (parseError) {
                            console.error("Failed to parse SSE data:", parseError);
                        }
                    }
                }
            }
        } catch (e) {
            console.error(e);
        } finally {
            setIsTyping(false);
        }
    };

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setAttachments((prev) => [...prev, e.target.files![0]]);
        }
    };

    const removeAttachment = (index: number) => {
        setAttachments((prev) => prev.filter((_, i) => i !== index));
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const handleConfirmApprove = async () => {
        if (!sessionId) return;

        setIsConfirming(true);
        try {
            const token = await user?.getIdToken();
            const res = await fetch(`/api/generate/confirm`, {
                method: "POST",
                headers: {
                    "Authorization": `Bearer ${token}`,
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ session_id: sessionId })
            });

            if (res.ok) {
                const data = await res.json();
                setPendingConfirmation(null);

                // Add success message
                setMessages(prev => [...prev, {
                    id: Date.now().toString(),
                    role: "assistant",
                    content: "**Requirements confirmed!** I'm now ready to generate your presentation outline."
                }]);

                // Trigger blueprint generation
                if (onOrderComplete && sessionId) {
                    setTimeout(() => {
                        onOrderComplete(sessionId);
                    }, 1500);
                }
            } else {
                const err = await res.json();
                setError(err.detail || "Failed to confirm");
            }
        } catch (e) {
            console.error("Confirmation failed:", e);
            setError("Failed to confirm. Please try again.");
        } finally {
            setIsConfirming(false);
        }
    };

    const handleCopyTranscript = async () => {
        try {
            const transcript = messages.map(m => `${m.role.toUpperCase()}: ${m.content}`).join("\n\n");
            await navigator.clipboard.writeText(transcript);
            setIsCopied(true);
            setTimeout(() => setIsCopied(false), 2000);
        } catch (err) {
            console.error("Failed to copy transcript", err);
        }
    };

    return (
        <div className="flex h-full flex-col">
            {/* Header / Toolbar */}
            <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-800 bg-neutral-900/50">
                <span className="text-xs text-neutral-500 uppercase font-medium">Chat Session</span>
                <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-xs text-neutral-400 hover:text-white transition-all w-24"
                    onClick={handleCopyTranscript}
                >
                    {isCopied ? (
                        <span className="flex items-center text-emerald-500">
                            <Check className="w-3 h-3 mr-1" /> Copied
                        </span>
                    ) : (
                        "Copy Transcript"
                    )}
                </Button>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-6 scrollbar-thin scrollbar-thumb-neutral-800 scrollbar-track-transparent">
                <AnimatePresence initial={false}>
                    {messages.map((msg) => (
                        <motion.div
                            key={msg.id}
                            initial={{ opacity: 0, y: 10, scale: 0.95 }}
                            animate={{ opacity: 1, y: 0, scale: 1 }}
                            className={cn(
                                "flex w-full gap-3",
                                msg.role === "user" ? "flex-row-reverse" : "flex-row"
                            )}
                        >
                            {/* Avatar */}
                            <div className={cn(
                                "flex h-8 w-8 shrink-0 items-center justify-center rounded-full border shadow-sm mt-1 transition-colors",
                                msg.role === "assistant"
                                    ? "bg-neutral-900 border-emerald-500/30 text-emerald-500"
                                    : "bg-neutral-800 border-white/10 text-neutral-300"
                            )}>
                                {msg.role === "assistant" ? <Bot className="h-4 w-4" /> : <User className="h-4 w-4" />}
                            </div>

                            {/* Bubble */}
                            <div className="flex max-w-[85%] flex-col gap-2">
                                <div className={cn(
                                    "relative rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-md transition-all",
                                    msg.role === "assistant"
                                        ? "bg-neutral-900 border border-neutral-800 text-neutral-200"
                                        : "bg-gradient-to-br from-emerald-600 to-emerald-700 text-white shadow-emerald-900/20"
                                )}>
                                    {msg.role === "assistant" ? (
                                        <div className="prose prose-invert prose-emerald prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-neutral-900 prose-pre:border prose-pre:border-white/10">
                                            {/* Thinking Trace (Collapsible) */}
                                            {msg.thinking && (
                                                <details className="mb-4 rounded-lg bg-neutral-950/50 border border-neutral-800 open:border-emerald-500/30 transition-all">
                                                    <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-neutral-500 hover:text-emerald-400 select-none flex items-center gap-2">
                                                        <span className="opacity-70">🧠 Thought Process</span>
                                                    </summary>
                                                    <div className="px-3 pb-3 pt-1 text-xs text-neutral-400 font-mono whitespace-pre-wrap leading-relaxed border-t border-white/5">
                                                        {msg.thinking}
                                                    </div>
                                                </details>
                                            )}

                                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                                {msg.content}
                                            </ReactMarkdown>
                                        </div>
                                    ) : (
                                        <div className="whitespace-pre-wrap">{msg.content}</div>
                                    )}

                                    {/* Attachment Display in bubble */}
                                    {msg.attachments && msg.attachments.length > 0 && (
                                        <div className="mt-3 flex flex-wrap gap-2">
                                            {msg.attachments.map((file, i) => (
                                                <div key={i} className="flex items-center gap-2 rounded-md bg-black/20 px-2 py-1.5 text-xs font-medium text-white/90 border border-white/10">
                                                    <FileIcon className="h-3.5 w-3.5" />
                                                    <span className="max-w-[150px] truncate">{file.name}</span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>
                        </motion.div>
                    ))}
                </AnimatePresence>

                {isTyping && (
                    <motion.div
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="flex items-center gap-3"
                    >
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-neutral-900 border border-emerald-500/30 text-emerald-500 shadow-sm">
                            <Loader2 className="h-4 w-4 animate-spin" />
                        </div>
                        <div className="flex items-center gap-2 rounded-full bg-neutral-900 px-4 py-2 border border-neutral-800">
                            <span className="text-xs text-neutral-400 animate-pulse">
                                AI is thinking...
                            </span>
                        </div>
                    </motion.div>
                )}
                {error && (
                    <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="flex w-full justify-center p-4"
                    >
                        <div className="rounded-lg bg-red-500/10 border border-red-500/20 p-3 text-sm text-red-500 flex items-center gap-2">
                            <span className="font-semibold">Error:</span> {error}
                        </div>
                    </motion.div>
                )}

                {/* Confirmation Card */}
                {pendingConfirmation && (
                    <div className="py-4">
                        <ConfirmationCard
                            summary={pendingConfirmation.summary}
                            message={pendingConfirmation.message}
                            onApprove={handleConfirmApprove}
                            onEdit={() => setPendingConfirmation(null)}
                            isLoading={isConfirming}
                        />
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t border-white/10 bg-neutral-950 p-4 sticky bottom-0 z-20">
                {/* Attachment Staging */}
                <AnimatePresence>
                    {attachments.length > 0 && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: "auto" }}
                            exit={{ opacity: 0, height: 0 }}
                            className="mb-3 flex flex-wrap gap-2 overflow-hidden"
                        >
                            {attachments.map((file, i) => (
                                <motion.div
                                    key={i}
                                    initial={{ opacity: 0, scale: 0.8 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    exit={{ opacity: 0, scale: 0.8 }}
                                    className="flex items-center gap-2 rounded-lg bg-neutral-900 px-3 py-2 text-xs text-neutral-300 border border-neutral-800"
                                >
                                    <FileIcon className="h-3.5 w-3.5 text-emerald-500" />
                                    <span className="max-w-[200px] truncate">{file.name}</span>
                                    <button onClick={() => removeAttachment(i)} className="ml-1 rounded-full p-0.5 hover:bg-neutral-800 text-neutral-500 hover:text-white transition-colors">
                                        <X className="h-3 w-3" />
                                    </button>
                                </motion.div>
                            ))}
                        </motion.div>
                    )}
                </AnimatePresence>

                <div className="relative flex items-end gap-2 rounded-xl border border-neutral-800 bg-neutral-900/50 p-2 shadow-inner focus-within:border-emerald-500/50 focus-within:ring-1 focus-within:ring-emerald-500/20 transition-all">
                    <input
                        type="file"
                        multiple
                        ref={fileInputRef}
                        className="hidden"
                        onChange={handleFileSelect}
                        accept=".pdf,.txt,.md,.png,.jpg,.jpeg"
                    />

                    <Button
                        variant="ghost"
                        size="icon"
                        className="h-9 w-9 shrink-0 rounded-lg text-neutral-400 hover:bg-neutral-800 hover:text-emerald-400 transition-colors"
                        onClick={() => fileInputRef.current?.click()}
                    >
                        <Paperclip className="h-4.5 w-4.5" />
                        <span className="sr-only">Attach file</span>
                    </Button>

                    <Textarea
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Type your message..."
                        className="min-h-[44px] max-h-[150px] w-full resize-none border-none bg-transparent px-2 py-2.5 text-sm text-neutral-200 placeholder:text-neutral-500 focus-visible:ring-0 active:outline-none"
                    />

                    <Button
                        size="icon"
                        className={cn(
                            "h-9 w-9 shrink-0 rounded-lg transition-all shadow-sm",
                            input.trim() || attachments.length > 0
                                ? "bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-900/20"
                                : "bg-neutral-800 text-neutral-500 cursor-not-allowed"
                        )}
                        onClick={handleSend}
                        disabled={(!input.trim() && attachments.length === 0) || isTyping}
                    >
                        {isTyping ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                        <span className="sr-only">Send</span>
                    </Button>
                </div>
                <p className="mt-2 text-center text-[10px] text-neutral-600">
                    SankoSlides AI can make mistakes. Review generated content.
                </p>
            </div>
        </div>
    );
}
