// lib/api-client.ts
// Generic API client for SankoSlides backend

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class APIError extends Error {
    constructor(
        public status: number,
        message: string,
        public details?: unknown
    ) {
        super(message);
        this.name = 'APIError';
    }
}

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
            throw new APIError(
                response.status,
                error.detail || `Request failed: ${response.statusText}`,
                error
            );
        }

        // Handle empty responses
        const text = await response.text();
        if (!text) {
            return {} as T;
        }

        return JSON.parse(text);
    }

    async get<T>(endpoint: string, headers?: Record<string, string>): Promise<T> {
        return this.request<T>(endpoint, { method: 'GET', headers });
    }

    async post<T>(
        endpoint: string,
        data?: unknown,
        headers?: Record<string, string>
    ): Promise<T> {
        return this.request<T>(endpoint, {
            method: 'POST',
            body: data ? JSON.stringify(data) : undefined,
            headers,
        });
    }

    getBaseUrl(): string {
        return this.baseUrl;
    }
}

export const api = new APIClient(API_URL);

// Helper to get API URL for SSE (which needs direct connection)
export function getAPIUrl(): string {
    return API_URL;
}
