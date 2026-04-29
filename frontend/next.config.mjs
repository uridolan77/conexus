/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: {
    NEXT_PUBLIC_BACKEND_BASE_URL:
      process.env.BACKEND_BASE_URL ?? "http://localhost:8000",
  },
};

export default nextConfig;
