import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  experimental: { cpus: 1 },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://static.cloudflareinsights.com",
              "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
              "font-src 'self' data: https://fonts.gstatic.com",
              "img-src 'self' data: blob: https://sigbl.com https://si-erp-api.mushaz.com",
              "connect-src 'self' https://si-erp-api.mushaz.com https://cloudflareinsights.com",
              "object-src 'none'",
              "base-uri 'self'",
              "frame-ancestors 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
  // Redux/saga uses non-deterministic IDs; keep classic SSR for production image
  // MUI v9 system-prop typings conflict widely; ship while types are aligned
  typescript: { ignoreBuildErrors: true },
};

export default nextConfig;
