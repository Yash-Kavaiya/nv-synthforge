import type { NextConfig } from "next";

const publicApiOrigin = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");
const apiOrigin = (process.env.BACKEND_INTERNAL_URL ?? publicApiOrigin).replace(/\/$/, "");

const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  async rewrites() {
    return [
      { source: "/backend-api/:path*", destination: `${apiOrigin}/:path*` },
      { source: "/backend-artifacts/:path*", destination: `${apiOrigin}/artifacts/:path*` },
    ];
  },
};

export default nextConfig;
