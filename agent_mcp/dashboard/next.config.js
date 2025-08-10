/** @type {import('next').NextConfig} */
const nextConfig = {
  // Disable image optimization for now
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
  
  typescript: {
    ignoreBuildErrors: true,
  },
};

module.exports = nextConfig;