export interface ClarifierChoiceOption {
    id: string;
    label: string;
    description?: string;
}

function slugifyLabel(label: string): string {
    return label
        .toLowerCase()
        .trim()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-+|-+$/g, "")
        .slice(0, 48) || "option";
}

function dedupeOptions(options: ClarifierChoiceOption[]): ClarifierChoiceOption[] {
    const seen = new Set<string>();
    const result: ClarifierChoiceOption[] = [];
    for (const option of options) {
        const key = option.label.toLowerCase().trim();
        if (!key || seen.has(key)) continue;
        seen.add(key);
        result.push(option);
    }
    return result;
}

function splitListSegment(segment: string): string[] {
    return segment
        .replace(/\s+(and|or)\s+/gi, ", ")
        .split(",")
        .map((entry) =>
            entry
                .replace(/^\s*(?:the|a|an)\s+/i, "")
                .replace(/^[\-\u2022*]\s*/, "")
                .replace(/\s+/g, " ")
                .trim()
        )
        .filter((entry) => entry.length >= 3);
}

function extractExampleOptions(questionText: string): string[] {
    const examples: string[] = [];
    const patterns = [
        /(?:such as|for example|e\.g\.,?)\s*([^)?.!]+)/gi,
        /\((?:e\.g\.,?|for example)\s*([^)]+)\)/gi,
    ];
    for (const pattern of patterns) {
        let match: RegExpExecArray | null = pattern.exec(questionText);
        while (match) {
            const segment = match[1]?.trim();
            if (segment) {
                examples.push(...splitListSegment(segment));
            }
            match = pattern.exec(questionText);
        }
    }
    return dedupeOptions(
        examples.map((label, index) => ({ id: `example-${index + 1}-${slugifyLabel(label)}`, label }))
    ).map((option) => option.label);
}

export function normalizeSuggestedOptions(raw: unknown): ClarifierChoiceOption[] {
    if (!Array.isArray(raw)) return [];
    const normalized: ClarifierChoiceOption[] = raw
        .map((entry, index) => {
            if (typeof entry === "string") {
                const label = entry.trim();
                if (!label) return null;
                return { id: `option-${index + 1}-${slugifyLabel(label)}`, label };
            }
            if (!entry || typeof entry !== "object") return null;

            const record = entry as Record<string, unknown>;
            const label = typeof record.label === "string"
                ? record.label.trim()
                : typeof record.value === "string"
                    ? record.value.trim()
                    : "";
            if (!label) return null;

            const baseId = typeof record.id === "string" ? record.id.trim() : "";
            return {
                id: baseId || `option-${index + 1}-${slugifyLabel(label)}`,
                label,
                description:
                    typeof record.description === "string" && record.description.trim()
                        ? record.description.trim()
                        : undefined,
            };
        })
        .filter((entry): entry is ClarifierChoiceOption => !!entry);

    return dedupeOptions(normalized);
}

export function inferSuggestedOptions(questionText: string): ClarifierChoiceOption[] {
    const normalizedQuestion = questionText.toLowerCase();

    if (normalizedQuestion.includes("target audience")) {
        return [
            { id: "audience-it-security-professionals", label: "IT security professionals" },
            { id: "audience-business-executives", label: "Business executives" },
            { id: "audience-general-corporate", label: "General corporate audience" },
        ];
    }

    if (normalizedQuestion.includes("how many") && normalizedQuestion.includes("slide")) {
        return [
            { id: "slides-8", label: "8 slides" },
            { id: "slides-10", label: "10 slides" },
            { id: "slides-15", label: "15 slides" },
            { id: "slides-auto", label: "Let AI decide" },
        ];
    }

    if (normalizedQuestion.includes("citation")) {
        return [
            { id: "citation-apa", label: "APA" },
            { id: "citation-ieee", label: "IEEE" },
            { id: "citation-harvard", label: "Harvard" },
            { id: "citation-chicago", label: "Chicago" },
        ];
    }

    if (
        normalizedQuestion.includes("source") &&
        (normalizedQuestion.includes("document") || normalizedQuestion.includes("pdf"))
    ) {
        return [
            { id: "source-pdf-only", label: "Use only uploaded documents" },
            { id: "source-pdf-plus-research", label: "Use documents plus external research" },
        ];
    }

    if (normalizedQuestion.includes("style") || normalizedQuestion.includes("tone")) {
        return [
            { id: "tone-academic", label: "Academic" },
            { id: "tone-technical", label: "Technical" },
            { id: "tone-persuasive", label: "Persuasive" },
            { id: "tone-conversational", label: "Conversational" },
        ];
    }

    const examples = extractExampleOptions(questionText);
    if (examples.length >= 2) {
        return examples.map((label, index) => ({
            id: `example-${index + 1}-${slugifyLabel(label)}`,
            label,
        }));
    }

    return [];
}

export function resolveSuggestedOptions(questionText: string, raw: unknown): ClarifierChoiceOption[] {
    const normalized = normalizeSuggestedOptions(raw);
    if (normalized.length > 0) return normalized;
    return inferSuggestedOptions(questionText);
}
