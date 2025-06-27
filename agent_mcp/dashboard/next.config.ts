import type { NextConfig } from "next";

// Bundle analyzer
const withBundleAnalyzer = require('@next/bundle-analyzer')({
  enabled: process.env.ANALYZE === 'true',
})

const nextConfig: NextConfig = {
  // Enable static export for serving through Python backend (only in production)
  output: process.env.NODE_ENV === 'production' ? 'export' : undefined,
  
  // Configure output directory to be the static folder (only for production builds)
  distDir: process.env.NODE_ENV === 'production' ? '../static' : '.next',
  
  // Disable image optimization for static export
  images: {
    unoptimized: true
  },
  
  // Configure trailing slash for better static serving
  trailingSlash: true,
  
  // Base path configuration (can be updated if needed)
  basePath: '',
  
  // Asset prefix for CDN support if needed later
  assetPrefix: '',

  eslint: {
    ignoreDuringBuilds: true,
  },
};

export default withBundleAnalyzer(nextConfig);
