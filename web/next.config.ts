import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  basePath: '/Privacy-Display',
  assetPrefix: '/Privacy-Display/',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
