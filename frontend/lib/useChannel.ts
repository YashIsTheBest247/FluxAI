"use client";

import { useEffect, useState } from "react";
import { health, type Health } from "./api";

let _cached: Health | null = null;
const _listeners = new Set<(h: Health | null) => void>();

async function loadOnce() {
  if (_cached !== null) return;
  try {
    _cached = await health();
  } catch {
    _cached = { status: "down", mock_mode: false, version: "?" };
  }
  _listeners.forEach((fn) => fn(_cached));
}

function useHealth(): Health | null {
  const [h, setH] = useState<Health | null>(_cached);
  useEffect(() => {
    _listeners.add(setH);
    loadOnce();
    return () => {
      _listeners.delete(setH);
    };
  }, []);
  return h;
}

/** Operator-configured Flux Channel URL, or null if not set. */
export function useChannelUrl(): string | null {
  const h = useHealth();
  return h?.channel_url ?? null;
}

/** True when the backend is generating placeholder content instead of real AI output. */
export function useMockMode(): boolean {
  const h = useHealth();
  return !!h?.mock_mode;
}
