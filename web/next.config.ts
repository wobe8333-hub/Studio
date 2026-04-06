import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Docker 배포용 standalone 빌드
  // Vercel 배포 시에는 이 줄을 제거하거나 주석 처리
  output: 'standalone',
};

export default nextConfig;
