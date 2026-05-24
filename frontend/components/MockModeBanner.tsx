"use client";

import { AlertTriangle } from "lucide-react";
import { useMockMode } from "@/lib/useChannel";

/**
 * Thin warning strip pinned just below the navbar — only renders when the backend
 * is in mock mode (skipping all paid APIs and returning placeholder content).
 */
export default function MockModeBanner() {
  const mock = useMockMode();
  if (!mock) return null;
  return (
    <div className="fixed inset-x-0 top-20 z-40 border-b border-red-deep/40 bg-red-tint/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center gap-3 px-6 py-2 text-[11px] font-medium uppercase tracking-widest text-red">
        <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
        <span className="truncate">
          MOCK MODE · placeholder content only ·{" "}
          <span className="text-ink-soft normal-case tracking-normal">
            set <code className="rounded bg-red-deep/20 px-1 font-mono text-[10px] text-ink">MOCK_MODE=false</code>{" "}
            in <code className="rounded bg-red-deep/20 px-1 font-mono text-[10px] text-ink">backend/.env</code> to use real OpenAI output
          </span>
        </span>
      </div>
    </div>
  );
}
