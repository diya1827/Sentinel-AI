import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Standalone output produces a minimal, self-contained server bundle
  // that the Docker image copies — smaller, faster production images.
  output: "standalone",
};

export default nextConfig;
