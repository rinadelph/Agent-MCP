import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable static export for serving through Python backend
  output: 'export',
  
  // Configure output directory to be the static folder
  distDir: '../static',
  
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
};

export default nextConfig;
