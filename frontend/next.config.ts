import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // Photos are served from the Pexels image network while placeholders are in use.
    // Remove this entry once every image in lib/images.ts points at a local file.
    remotePatterns: [
      { protocol: "https", hostname: "images.pexels.com", pathname: "/photos/**" },
    ],
  },
};

export default nextConfig;
