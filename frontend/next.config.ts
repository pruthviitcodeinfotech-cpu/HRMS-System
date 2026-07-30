import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Required for production Docker deployment.
  // Produces .next/standalone/ — a self-contained Node.js server with
  // only the node_modules required at runtime (~80% smaller image).
  output: "standalone",
};

export default nextConfig;
