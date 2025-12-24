// types/generation.ts
// TypeScript interfaces for SankoSlides Generation API

// ============================================================================
// Session & Start
// ============================================================================

export interface StartSessionResponse {
    session_id: string;
    status: string;
    message: string;
}

// ============================================================================
// Clarification
// ============================================================================

export interface ClarifyRequest {
    message: string;
}

export interface ClarifyResponse {
    session_id: string;
    complete: boolean;
    question?: string;
    order_form?: OrderForm;
}

export interface OrderForm {
    presentation_title: string;
    target_audience: string;
    target_slides: number;
    theme_id: string;
    citation_style: string;
    key_topics: string[];
    focus_areas: string[];
    emphasis_style: string;
    include_speaker_notes: boolean;
    is_complete: boolean;
}

// ============================================================================
// Outline / Skeleton
// ============================================================================

export interface Skeleton {
    presentation_title: string;
    target_audience: string;
    narrative_arc: string;
    slides: SkeletonSlide[];
    estimated_duration_minutes: number;
}

export interface SkeletonSlide {
    order: number;
    title: string;
    content_type: string;
    description: string;
    needs_diagram: boolean;
    needs_equation: boolean;
    needs_citation: boolean;
    citation_topic?: string;
}

export interface OutlineResponse {
    session_id: string;
    status: string;
    skeleton: Skeleton;
}

// ============================================================================
// Modifications
// ============================================================================

export interface Modification {
    action: 'add' | 'remove' | 'modify' | 'reorder';
    order?: number;
    title?: string;
    content_type?: string;
    description?: string;
    new_order?: number[];
    needs_diagram?: boolean;
    needs_equation?: boolean;
    needs_citation?: boolean;
}

export interface ApproveRequest {
    modifications?: Modification[];
}

// ============================================================================
// Generation
// ============================================================================

export interface GenerationStartResponse {
    session_id: string;
    status: string;
    total_slides: number;
    message: string;
}

export interface SessionStatusResponse {
    session_id: string;
    status: SessionStatus;
    current_stage: string;
    slides_completed: number;
    total_slides: number;
    order_form?: OrderForm;
    skeleton?: Skeleton;
    qa_score?: number;
}

export type SessionStatus =
    | 'awaiting_clarification'
    | 'clarification_complete'
    | 'awaiting_outline_approval'
    | 'outline_approved'
    | 'generating'
    | 'qa_in_progress'
    | 'completed'
    | 'failed';

// ============================================================================
// Result
// ============================================================================

export interface GeneratedSlide {
    order: number;
    title: string;
    theme_id: string;
    rendered_html: string;
    speaker_notes?: string;
}

export interface GeneratedPresentation {
    title: string;
    theme_id: string;
    slides: GeneratedSlide[];
    total_slides: number;
}

export interface QAResult {
    slide_order: number;
    score: number;
    issues: string[];
    passed: boolean;
    iterations?: number;
}

export interface QAReport {
    session_id: string;
    slides: QAResult[];
    average_score: number;
    all_passed: boolean;
    total_iterations: number;
}

export interface GenerationResult {
    session_id: string;
    presentation: GeneratedPresentation;
    qa_report?: QAReport;
}

// ============================================================================
// Metrics
// ============================================================================

export interface MetricsSummary {
    session_id: string;
    input_tokens: number;
    output_tokens: number;
    thinking_tokens: number;
    total_tokens: number;
    cost_usd: number;
    api_calls: number;
    status: string;
}

// ============================================================================
// SSE Events
// ============================================================================

export interface SSEStageStartEvent {
    type: 'stage_start';
    stage: string;
}

export interface SSEStageCompleteEvent {
    type: 'stage_complete';
    stage: string;
    result?: Record<string, unknown>;
}

export interface SSESlideProgressEvent {
    type: 'slide_progress';
    slide_order: number;
    total: number;
    status: string;
}

export interface SSECompleteEvent {
    type: 'complete';
    slides_count: number;
}

export interface SSEErrorEvent {
    type: 'error';
    message: string;
    stage?: string;
}

export type SSEEvent =
    | SSEStageStartEvent
    | SSEStageCompleteEvent
    | SSESlideProgressEvent
    | SSECompleteEvent
    | SSEErrorEvent;
