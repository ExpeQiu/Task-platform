import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Task Platform - 任务编排中心",
  description: "Task Platform MVP",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
