# Frontend Integration Guide

How to integrate the SankoSlides backend with your frontend application.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [API Client Setup](#api-client-setup)
- [Generation Flow](#generation-flow)
- [SSE Streaming](#sse-streaming)
- [State Management](#state-management)
- [Error Handling](#error-handling)
- [TypeScript Types](#typescript-types)

---

## Overview

The SankoSlides backend provides a REST API with SSE streaming for real-time progress updates. This guide covers integration patterns for React/Next.js frontends.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Frontend                                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │
│   │   Playground │    │    Editor    │    │  Dashboard   │        │
│   │  Component   │    │  Component   │    │  Component   │        │
│   └──────┬───────┘    └──────┬───────┘    └──────────────┘        │
│          │                   │                                      │
│          └─────────┬─────────┘                                     │
│                    │                                                │
│                    ▼                                                │
│          ┌──────────────────┐                                      │
│          │   API Client     │                                      │
│          │   (fetch/axios)  │                                      │
│          └────────┬─────────┘                                      │
│                   │                                                 │
└───────────────────┼─────────────────────────────────────────────────┘
                    │
                    ▼
         ┌──────────────────┐
         │  SankoSlides     │
         │  Backend API     │
         │  :8000           │
         └──────────────────┘
```

---

## Architecture

### Environment Configuration

```env
# .env.local (Next.js)
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### CORS Configuration

Backend is configured to allow:
- `http://localhost:3000` (Next.js dev)
- Your production frontend URL

---

## API Client Setup

### Base Client

```typescript
// lib/api-client.ts

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new APIError(response.status, error.detail || 'Request failed');
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET' });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }
}

class APIError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'APIError';
  }
}

export const api = new APIClient(API_URL);
```

### Generation API Module

```typescript
// lib/api/generation.ts

import { api } from '../api-client';
import type {
  StartSessionResponse,
  ClarifyRequest,
  ClarifyResponse,
  OutlineResponse,
  ApproveRequest,
  GenerationStartResponse,
  SessionStatusResponse,
  GenerationResult,
  MetricsSummary,
} from '@/types/generation';

export const generationApi = {
  // Start a new session
  startSession: () =>
    api.post<StartSessionResponse>('/api/generation/start'),

  // Continue clarification
  clarify: (sessionId: string, message: string) =>
    api.post<ClarifyResponse>(`/api/generation/clarify/${sessionId}`, {
      message,
    }),

  // Generate outline
  getOutline: (sessionId: string) =>
    api.post<OutlineResponse>(`/api/generation/outline/${sessionId}`),

  // Approve outline (with optional modifications)
  approveOutline: (sessionId: string, modifications?: ApproveRequest['modifications']) =>
    api.post<OutlineResponse>(`/api/generation/approve-outline/${sessionId}`, {
      modifications,
    }),

  // Start generation
  startGeneration: (sessionId: string) =>
    api.post<GenerationStartResponse>(`/api/generation/generate/${sessionId}`),

  // Get status
  getStatus: (sessionId: string) =>
    api.get<SessionStatusResponse>(`/api/generation/status/${sessionId}`),

  // Get final result
  getResult: (sessionId: string) =>
    api.get<GenerationResult>(`/api/generation/result/${sessionId}`),

  // Get metrics
  getMetrics: (sessionId: string) =>
    api.get<MetricsSummary>(`/api/generation/metrics/${sessionId}/summary`),

  // Quick start (skip clarification)
  quickStart: (title: string, topic: string, slidesCount = 8) =>
    api.post<GenerationStartResponse>(
      `/api/generation/quick-start?title=${encodeURIComponent(title)}&topic=${encodeURIComponent(topic)}&slides_count=${slidesCount}`
    ),
};
```

---

## Generation Flow

### Complete Flow Example

```tsx
// components/playground/generation-flow.tsx

import { useState, useCallback } from 'react';
import { generationApi } from '@/lib/api/generation';
import { useGenerationStream } from '@/hooks/use-generation-stream';

type FlowStep = 'idle' | 'clarifying' | 'outline' | 'generating' | 'complete' | 'error';

export function GenerationFlow() {
  const [step, setStep] = useState<FlowStep>('idle');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [skeleton, setSkeleton] = useState<Skeleton | null>(null);
  const [result, setResult] = useState<GenerationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Start new session
  const startSession = useCallback(async () => {
    try {
      const response = await generationApi.startSession();
      setSessionId(response.session_id);
      setStep('clarifying');
      setMessages([{
        role: 'assistant',
        content: 'What would you like to create a presentation about?',
      }]);
    } catch (err) {
      setError('Failed to start session');
      setStep('error');
    }
  }, []);

  // Send clarification message
  const sendMessage = useCallback(async (message: string) => {
    if (!sessionId) return;

    setMessages(prev => [...prev, { role: 'user', content: message }]);

    try {
      const response = await generationApi.clarify(sessionId, message);

      if (response.complete) {
        // Move to outline generation
        setStep('outline');
        const outlineResponse = await generationApi.getOutline(sessionId);
        setSkeleton(outlineResponse.skeleton);
      } else {
        // Add follow-up question
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: response.question!,
        }]);
      }
    } catch (err) {
      setError('Failed to process message');
    }
  }, [sessionId]);

  // Approve outline
  const approveOutline = useCallback(async (modifications?: Modification[]) => {
    if (!sessionId) return;

    try {
      await generationApi.approveOutline(sessionId, modifications);
      await generationApi.startGeneration(sessionId);
      setStep('generating');
    } catch (err) {
      setError('Failed to start generation');
    }
  }, [sessionId]);

  // SSE streaming for generation progress
  const { progress, isComplete } = useGenerationStream(
    step === 'generating' ? sessionId : null,
    {
      onComplete: async () => {
        const resultResponse = await generationApi.getResult(sessionId!);
        setResult(resultResponse);
        setStep('complete');
      },
      onError: (message) => {
        setError(message);
        setStep('error');
      },
    }
  );

  return (
    <div className="generation-flow">
      {step === 'idle' && (
        <button onClick={startSession}>Start New Presentation</button>
      )}

      {step === 'clarifying' && (
        <ClarificationChat
          messages={messages}
          onSendMessage={sendMessage}
        />
      )}

      {step === 'outline' && skeleton && (
        <OutlineEditor
          skeleton={skeleton}
          onApprove={approveOutline}
          onModify={(mods) => approveOutline(mods)}
        />
      )}

      {step === 'generating' && progress && (
        <GenerationProgress
          currentStage={progress.stage}
          slidesCompleted={progress.slidesCompleted}
          totalSlides={progress.totalSlides}
        />
      )}

      {step === 'complete' && result && (
        <PresentationViewer presentation={result.presentation} />
      )}

      {step === 'error' && (
        <ErrorDisplay message={error!} onRetry={startSession} />
      )}
    </div>
  );
}
```

---

## SSE Streaming

### Hook for Generation Stream

```tsx
// hooks/use-generation-stream.ts

import { useEffect, useState, useRef } from 'react';

interface StreamProgress {
  stage: string;
  slidesCompleted: number;
  totalSlides: number;
}

interface UseGenerationStreamOptions {
  onComplete?: () => void;
  onError?: (message: string) => void;
  onStageChange?: (stage: string) => void;
  onSlideProgress?: (slideOrder: number, total: number) => void;
}

export function useGenerationStream(
  sessionId: string | null,
  options: UseGenerationStreamOptions = {}
) {
  const [progress, setProgress] = useState<StreamProgress | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!sessionId) return;

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const eventSource = new EventSource(
      `${API_URL}/api/generation/stream/${sessionId}`
    );
    eventSourceRef.current = eventSource;

    eventSource.addEventListener('stage_start', (e) => {
      const data = JSON.parse(e.data);
      setProgress(prev => ({ ...prev!, stage: data.stage }));
      options.onStageChange?.(data.stage);
    });

    eventSource.addEventListener('slide_progress', (e) => {
      const data = JSON.parse(e.data);
      setProgress(prev => ({
        ...prev!,
        slidesCompleted: data.slide_order,
        totalSlides: data.total,
      }));
      options.onSlideProgress?.(data.slide_order, data.total);
    });

    eventSource.addEventListener('complete', () => {
      setIsComplete(true);
      eventSource.close();
      options.onComplete?.();
    });

    eventSource.addEventListener('error', (e: any) => {
      if (e.data) {
        const data = JSON.parse(e.data);
        options.onError?.(data.message);
      }
      eventSource.close();
    });

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [sessionId]);

  return { progress, isComplete };
}
```

### Progress Component

```tsx
// components/playground/generation-progress.tsx

interface GenerationProgressProps {
  currentStage: string;
  slidesCompleted: number;
  totalSlides: number;
}

const STAGES = [
  { id: 'planner', label: 'Planning Content' },
  { id: 'refiner', label: 'Rendering Assets' },
  { id: 'generator', label: 'Generating Slides' },
  { id: 'visual_qa', label: 'Quality Check' },
];

export function GenerationProgress({
  currentStage,
  slidesCompleted,
  totalSlides,
}: GenerationProgressProps) {
  const currentIndex = STAGES.findIndex(s => s.id === currentStage);
  const overallProgress = totalSlides > 0 
    ? (slidesCompleted / totalSlides) * 100 
    : 0;

  return (
    <div className="generation-progress">
      {/* Stage indicators */}
      <div className="stages">
        {STAGES.map((stage, index) => (
          <div
            key={stage.id}
            className={`stage ${
              index < currentIndex ? 'complete' :
              index === currentIndex ? 'active' : 'pending'
            }`}
          >
            <div className="stage-indicator">
              {index < currentIndex ? '✓' : index + 1}
            </div>
            <span className="stage-label">{stage.label}</span>
          </div>
        ))}
      </div>

      {/* Slide progress bar */}
      {currentStage === 'generator' && (
        <div className="slide-progress">
          <div className="progress-bar">
            <div
              className="progress-fill"
              style={{ width: `${overallProgress}%` }}
            />
          </div>
          <span className="progress-text">
            {slidesCompleted} / {totalSlides} slides
          </span>
        </div>
      )}
    </div>
  );
}
```

---

## State Management

### Using Zustand

```typescript
// stores/generation-store.ts

import { create } from 'zustand';
import type { Skeleton, GeneratedPresentation, OrderForm } from '@/types';

interface GenerationState {
  sessionId: string | null;
  status: string;
  orderForm: OrderForm | null;
  skeleton: Skeleton | null;
  presentation: GeneratedPresentation | null;
  
  // Actions
  setSessionId: (id: string) => void;
  setStatus: (status: string) => void;
  setOrderForm: (form: OrderForm) => void;
  setSkeleton: (skeleton: Skeleton) => void;
  setPresentation: (presentation: GeneratedPresentation) => void;
  reset: () => void;
}

export const useGenerationStore = create<GenerationState>((set) => ({
  sessionId: null,
  status: 'idle',
  orderForm: null,
  skeleton: null,
  presentation: null,

  setSessionId: (id) => set({ sessionId: id }),
  setStatus: (status) => set({ status }),
  setOrderForm: (form) => set({ orderForm: form }),
  setSkeleton: (skeleton) => set({ skeleton }),
  setPresentation: (presentation) => set({ presentation }),
  reset: () => set({
    sessionId: null,
    status: 'idle',
    orderForm: null,
    skeleton: null,
    presentation: null,
  }),
}));
```

### Using React Context

```tsx
// contexts/generation-context.tsx

import { createContext, useContext, useReducer, ReactNode } from 'react';

interface GenerationState {
  sessionId: string | null;
  status: string;
  skeleton: Skeleton | null;
  presentation: GeneratedPresentation | null;
}

type Action =
  | { type: 'START_SESSION'; sessionId: string }
  | { type: 'SET_STATUS'; status: string }
  | { type: 'SET_SKELETON'; skeleton: Skeleton }
  | { type: 'SET_PRESENTATION'; presentation: GeneratedPresentation }
  | { type: 'RESET' };

const initialState: GenerationState = {
  sessionId: null,
  status: 'idle',
  skeleton: null,
  presentation: null,
};

function reducer(state: GenerationState, action: Action): GenerationState {
  switch (action.type) {
    case 'START_SESSION':
      return { ...state, sessionId: action.sessionId, status: 'clarifying' };
    case 'SET_STATUS':
      return { ...state, status: action.status };
    case 'SET_SKELETON':
      return { ...state, skeleton: action.skeleton };
    case 'SET_PRESENTATION':
      return { ...state, presentation: action.presentation, status: 'complete' };
    case 'RESET':
      return initialState;
    default:
      return state;
  }
}

const GenerationContext = createContext<{
  state: GenerationState;
  dispatch: React.Dispatch<Action>;
} | null>(null);

export function GenerationProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <GenerationContext.Provider value={{ state, dispatch }}>
      {children}
    </GenerationContext.Provider>
  );
}

export function useGeneration() {
  const context = useContext(GenerationContext);
  if (!context) throw new Error('useGeneration must be used within GenerationProvider');
  return context;
}
```

---

## Error Handling

### Error Boundary

```tsx
// components/error-boundary.tsx

import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <p>{this.state.error?.message}</p>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

### API Error Handler

```typescript
// lib/error-handler.ts

export function handleAPIError(error: unknown): string {
  if (error instanceof APIError) {
    switch (error.status) {
      case 400:
        return `Invalid request: ${error.message}`;
      case 404:
        return 'Session not found. Please start a new session.';
      case 500:
        return 'Server error. Please try again later.';
      default:
        return error.message;
    }
  }
  
  if (error instanceof Error) {
    return error.message;
  }
  
  return 'An unexpected error occurred';
}
```

---

## TypeScript Types

### Type Definitions

```typescript
// types/generation.ts

export interface StartSessionResponse {
  session_id: string;
  status: string;
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

export interface ApproveRequest {
  modifications?: Modification[];
}

export interface Modification {
  action: 'add' | 'remove' | 'modify' | 'reorder';
  order?: number;
  title?: string;
  content_type?: string;
  description?: string;
  new_order?: number[];
}

export interface GenerationStartResponse {
  session_id: string;
  status: string;
  total_slides: number;
  message: string;
}

export interface SessionStatusResponse {
  session_id: string;
  status: string;
  current_stage: string;
  slides_completed: number;
  total_slides: number;
  order_form?: OrderForm;
  skeleton?: Skeleton;
  qa_score?: number;
}

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

export interface GenerationResult {
  session_id: string;
  presentation: GeneratedPresentation;
  qa_report?: QAReport;
}

export interface QAResult {
  slide_order: number;
  score: number;
  issues: string[];
  passed: boolean;
}

export interface QAReport {
  session_id: string;
  slides: QAResult[];
  average_score: number;
  all_passed: boolean;
  total_iterations: number;
}

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
```
