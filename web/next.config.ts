import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // PWA: 정적 export (Capacitor 빌드용)
  // Vercel 배포 시에는 output: 'export' 제거
  // output: 'export',

  // 이미지 최적화 (정적 export 시 unoptimized: true 필요)
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
