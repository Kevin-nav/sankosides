"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";

function makeQueryClient() {
    return new QueryClient({
        defaultOptions: {
            queries: {
                // Data is fresh for 30 seconds, then stale
                staleTime: 30 * 1000,
                // Keep unused data in cache for 5 minutes
                gcTime: 5 * 60 * 1000,
                // Retry 3 times with exponential backoff
                retry: 3,
                retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
                // Refetch on window focus for fresh data
                refetchOnWindowFocus: true,
                // Don't refetch on mount if data is fresh
                refetchOnMount: true,
            },
            mutations: {
                // Retry mutations once
                retry: 1,
            },
        },
    });
}

let browserQueryClient: QueryClient | undefined = undefined;

function getQueryClient() {
    if (typeof window === "undefined") {
        // Server: always make a new query client
        return makeQueryClient();
    } else {
        // Browser: reuse existing query client
        if (!browserQueryClient) browserQueryClient = makeQueryClient();
        return browserQueryClient;
    }
}

interface QueryProviderProps {
    children: React.ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps) {
    // Use useState to ensure the query client is only created once per component lifecycle
    const [queryClient] = useState(() => getQueryClient());

    return (
        <QueryClientProvider client={queryClient}>
            {children}
            {process.env.NODE_ENV === "development" && (
                <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
            )}
        </QueryClientProvider>
    );
}

// Export query client for manual cache manipulation
export { getQueryClient };
