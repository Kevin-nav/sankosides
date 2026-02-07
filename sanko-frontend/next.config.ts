import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: '20mb',
    },
  },
  turbopack: {
    // Explicitly set the workspace root to prevent lockfile detection issues
    root: __dirname,
  },
  async rewrites() {
    return [
      // Generation endpoint forwarding to backend
      // Note: Our /app/api/generate/* routes take precedence
      // This catches any unhandled paths
      {
        source: '/api/generation/:path*',
        destination: 'http://127.0.0.1:8000/api/generation/:path*',
      },
    ];
  },
};

export default nextConfig;
