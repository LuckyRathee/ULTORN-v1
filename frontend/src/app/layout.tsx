import type { Metadata } from "next";
import { Geist, Geist_Mono, Share_Tech_Mono, JetBrains_Mono } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const shareTechMono = Share_Tech_Mono({
  weight: "400",
  variable: "--font-share-tech-mono",
  subsets: ["latin"],
});

const jetBrainsMono = JetBrains_Mono({
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "ultron 2.0 // Tactical AI Command Center",
  description: "Next-Gen Sci-Fi HUD Voice AI Assistant & Autonomous Task Pipeline",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${shareTechMono.variable} ${jetBrainsMono.variable} h-full antialiased dark`}
    >
      <body className="min-h-full bg-[#030712] text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200 hud-scanlines">
        {children}
      </body>
    </html>
  );
}
