"use client";

import posthog from "posthog-js";
import { PostHogProvider } from "posthog-js/react";
import { useEffect } from "react";

type Props = {
  children: React.ReactNode;
};

export function SankoPostHogProvider({ children }: Props) {
  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_POSTHOG_KEY;
    if (!key) return;

    // Initialize once on the client.
    if ((posthog as unknown as { __sanko_inited?: boolean }).__sanko_inited) return;
    (posthog as unknown as { __sanko_inited?: boolean }).__sanko_inited = true;

    posthog.init(key, {
      api_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || "https://app.posthog.com",
      autocapture: true,
      capture_pageview: false, // we'll do manual pageviews for Next App Router
      capture_pageleave: true,
      person_profiles: "identified_only",
    });
  }, []);

  return <PostHogProvider client={posthog}>{children}</PostHogProvider>;
}

