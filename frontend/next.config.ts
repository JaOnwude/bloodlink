import type { NextConfig } from "next";

/**
 * Where the API runs when the site is deployed, for example
 * "https://bloodlink-api.onrender.com". Read when the site is built.
 *
 * When it is set, the site forwards every request under /api/v1 to the API, and the browser
 * is pointed at that same-site path (NEXT_PUBLIC_API_URL=/api/v1). The browser then talks
 * only to the site's own address, so the session cookie is an ordinary first-party cookie.
 * Calling the API's own address directly would make it a third-party cookie, which Safari
 * and other privacy-focused browsers block, and sign-in would fail there.
 *
 * Left unset during local development, where the browser calls the API on localhost:8000
 * directly (both are "localhost", so the cookie is first-party there too).
 */
const backendOrigin = process.env.BACKEND_ORIGIN?.replace(/\/+$/, "");

const nextConfig: NextConfig = {
  images: {
    // Photos are served from the Pexels image network while placeholders are in use.
    // Remove this entry once every image in lib/images.ts points at a local file.
    remotePatterns: [
      { protocol: "https", hostname: "images.pexels.com", pathname: "/photos/**" },
    ],
  },

  async rewrites() {
    if (!backendOrigin) return [];
    return [{ source: "/api/v1/:path*", destination: `${backendOrigin}/api/v1/:path*` }];
  },
};

export default nextConfig;
