import type { Metadata } from "next";
import { Inter, Bebas_Neue, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";
import MockModeBanner from "@/components/MockModeBanner";

const sans = Inter({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const display = Bebas_Neue({ subsets: ["latin"], weight: ["400"], variable: "--font-display", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });

export const metadata: Metadata = {
  title: "FLUX",
  description: "Type a topic. Get a finished video. Auto-published to YouTube.",
  metadataBase: new URL("http://localhost:3000"),
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${sans.variable} ${display.variable} ${mono.variable}`}>
      <body className="min-h-screen bg-bg text-ink antialiased">
        <Navbar />
        <MockModeBanner />
        <main className="pt-20">{children}</main>
        <Footer />
      </body>
    </html>
  );
}

function Footer() {
  return (
    <footer className="border-t border-line">
      <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-6 px-6 py-8 sm:flex-row sm:items-center">
        <div>
          <div className="flex items-baseline gap-1.5">
            <span className="display text-2xl tracking-tight">FLUX</span>
            <span className="display text-2xl leading-none text-red">.</span>
          </div>
          <p className="mt-1 text-xs text-ink-muted">Educational video, automated.</p>
        </div>
        <div className="flex items-center gap-6 text-[11px] uppercase tracking-widest text-ink-muted">
          <a href="/" className="hover:text-ink">Dashboard</a>
          <a href="/creator" className="hover:text-ink">Creator</a>
          <a href="/library" className="hover:text-ink">Library</a>
          <span className="font-mono text-ink-faint">© {new Date().getFullYear()}</span>
        </div>
      </div>
    </footer>
  );
}
