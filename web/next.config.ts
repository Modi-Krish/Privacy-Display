import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === 'production';

const nextConfig: NextConfig = {
  output: isProd ? 'export' : undefined,
  basePath: isProd ? '/Privacy-Display' : '',
  assetPrefix: isProd ? '/Privacy-Display/' : '',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
