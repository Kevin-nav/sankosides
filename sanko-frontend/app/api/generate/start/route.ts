// app/api/generate/start/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { resolveSuggestedOptions } from "@/lib/clarifier-options";

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

function normalizeSections(raw: unknown) {
    if (!Array.isArray(raw)) return [];
    return raw
        .map((entry, index) => {
            if (!entry || typeof entry !== "object") return null;
            const record = entry as Record<string, unknown>;
            return {
                id: String(record.id ?? record.section_id ?? record.key ?? `section-${index + 1}`),
                title: String(record.title ?? record.name ?? record.heading ?? `Section ${index + 1}`),
                preview: String(record.preview ?? record.summary ?? record.description ?? ""),
            };
        })
        .filter((entry): entry is { id: string; title: string; preview: string } => !!entry);
}

function normalizeQuestion(raw: unknown, sessionId?: string) {
    if (!raw || typeof raw !== "object") return null;
    const record = raw as Record<string, unknown>;
    const questionText =
        typeof record.question_text === "string"
            ? record.question_text
            : typeof record.question === "string"
                ? record.question
                : null;
    if (!questionText) return null;

    return {
        id: typeof record.id === "string" ? record.id : `${sessionId || "session"}-initial`,
        question_text: questionText,
        field_key: typeof record.field_key === "string" ? record.field_key : null,
        suggested_options: resolveSuggestedOptions(questionText, record.suggested_options),
        allow_custom: typeof record.allow_custom === "boolean" ? record.allow_custom : true,
        allow_multiple: typeof record.allow_multiple === "boolean" ? record.allow_multiple : false,
    };
}

export async function POST(request: NextRequest) {
    try {
        const body = await request.json().catch(() => ({}));
        const authHeader = request.headers.get("authorization");
        const fileHashes = Array.isArray(body.file_hashes) ? body.file_hashes : [];
        const wizardData = body.wizard_data && typeof body.wizard_data === "object" ? body.wizard_data : undefined;

        // Build URL with query parameters for session metadata
        const url = new URL(`${BACKEND_URL}/api/generation/start`);

        // Add optional parameters as query params
        if (body.project_id) {
            url.searchParams.append('project_id', body.project_id);
        }
        if (body.mode) {
            url.searchParams.append('mode', body.mode);
        }
        if (body.topic) {
            url.searchParams.append('topic', body.topic);
        }

        const response = await fetch(url.toString(), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...(authHeader ? { Authorization: authHeader } : {}),
            },
            // Backend endpoint accepts query params, not body for these fields
        });

        const data = await response.json();

        if (!response.ok) {
            return NextResponse.json(data, { status: response.status });
        }

        // Optional contract bridge for wizard:
        // if frontend already has file hashes or collected wizard data, seed clarification immediately.
        const shouldSeedClarification =
            !!data?.session_id && body.request_next_question === true;

        if (shouldSeedClarification) {
            try {
                const clarifyResponse = await fetch(`${BACKEND_URL}/api/generation/clarify/${data.session_id}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        ...(authHeader ? { Authorization: authHeader } : {}),
                    },
                    body: JSON.stringify({
                        message: body.topic || "Continue",
                        file_hashes: fileHashes.length > 0 ? fileHashes : undefined,
                        wizard_data: wizardData,
                        request_next_question: true,
                    }),
                });

                const clarifyData = await clarifyResponse.json().catch(() => ({}));
                if (clarifyResponse.ok) {
                    const normalizedSections = normalizeSections(
                        clarifyData.sections || clarifyData.document_sections || data.sections
                    );
                    return NextResponse.json({
                        ...data,
                        sections: normalizedSections,
                        next_step: clarifyData.complete ? "summary" : "clarify",
                        next_question: clarifyData.question
                            ? {
                                id: `${data.session_id}-initial`,
                                question_text: clarifyData.question,
                                field_key:
                                    typeof clarifyData.field_key === "string"
                                        ? clarifyData.field_key
                                        : null,
                                suggested_options: resolveSuggestedOptions(
                                    clarifyData.question,
                                    clarifyData.suggested_options
                                ),
                                allow_custom:
                                    typeof clarifyData.allow_custom === "boolean"
                                        ? clarifyData.allow_custom
                                        : true,
                                allow_multiple:
                                    typeof clarifyData.allow_multiple === "boolean"
                                        ? clarifyData.allow_multiple
                                        : false,
                            }
                            : null,
                        needs_confirmation: clarifyData.needs_confirmation ?? false,
                        summary: clarifyData.summary,
                        complete: clarifyData.complete ?? false,
                        clarify_message: clarifyData.message,
                    });
                }
            } catch (clarifyError) {
                console.error("Clarification seed after start failed:", clarifyError);
            }
        }

        const normalizedSections = normalizeSections(
            data.sections || data.document_sections || data.section_options
        );
        return NextResponse.json({
            ...data,
            sections: normalizedSections,
            next_question: normalizeQuestion(data.next_question, data.session_id),
        });
    } catch (error) {
        console.error('Start session error:', error);
        return NextResponse.json(
            { detail: 'Failed to connect to backend' },
            { status: 503 }
        );
    }
}
