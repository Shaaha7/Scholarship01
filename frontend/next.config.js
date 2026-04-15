  /** @type {import('next').NextConfig} */
const createNextIntlPlugin = require("next-intl/plugin");
const withNextIntl = createNextIntlPlugin("./src/i18n.ts");

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "scholarships.gov.in" },
      { protocol: "https", hostname: "tamilnadu.gov.in" },
    ],
  },
  async rewrites() {
    return [
      // Proxy API calls to the backend container (so public sharing works).
      {
        source: "/api/v1/:path*",
        destination: "http://tamilscholar_backend:8000/api/v1/:path*",
      },
      {
        source: "/api/backend/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL}/api/v1/:path*`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-DNS-Prefetch-Control", value: "on" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
        ],
      },
    ];
  },
};

module.exports = withNextIntl(nextConfig);
