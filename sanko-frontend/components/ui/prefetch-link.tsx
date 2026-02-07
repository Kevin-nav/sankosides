'use client';

import Link from 'next/link';
import { useCallback, useRef } from 'react';

interface PrefetchLinkProps {
    href: string;
    prefetchUrls?: string[];
    children: React.ReactNode;
    className?: string;
}

/**
 * A Link component that prefetches API data on hover (desktop) or touch start (mobile).
 * 
 * When users show intent to navigate (hover/touch), we proactively fetch data
 * to warm the backend cache. This makes the actual page load feel instant.
 * 
 * @example
 * <PrefetchLink 
 *   href="/dashboard/templates"
 *   prefetchUrls={['/api/templates', '/api/themes']}
 * >
 *   Templates
 * </PrefetchLink>
 */
export function PrefetchLink({
    href,
    prefetchUrls = [],
    children,
    className
}: PrefetchLinkProps) {
    // Track if we've already prefetched to avoid duplicate requests
    const hasPrefetched = useRef(false);

    const prefetch = useCallback(() => {
        // Only prefetch once per component mount
        if (hasPrefetched.current || prefetchUrls.length === 0) return;
        hasPrefetched.current = true;

        // Fire all prefetch requests in parallel (fire-and-forget)
        prefetchUrls.forEach(url => {
            // Use low priority fetch to not interfere with current page
            fetch(url, {
                priority: 'low',
                // Don't throw on errors - we're just warming the cache
            }).catch(() => { });
        });
    }, [prefetchUrls]);

    return (
        <Link
            href={href}
            className={className}
            onMouseEnter={prefetch}    // Desktop: hover
            onTouchStart={prefetch}    // Mobile: touch begins (before tap completes)
            onFocus={prefetch}         // Keyboard navigation: focus
        >
            {children}
        </Link>
    );
}

// Pre-defined prefetch configurations for common routes
// NOTE: With Convex, most data is automatically cached/synced client-side.
// Only add URLs here for non-Convex API endpoints that benefit from prefetching.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const PREFETCH_CONFIGS: Record<string, string[]> = {
    // templates: Previously fetched from backend, now served directly from Convex.
    // Convex queries use WebSocket subscriptions and don't need prefetch.
    templates: [],
    // Add non-Convex endpoints that benefit from prefetching here
};
