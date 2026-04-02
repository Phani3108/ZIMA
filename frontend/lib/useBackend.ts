"use client";

import { useState, useEffect } from "react";

/**
 * Simple hook that pings the backend health endpoint once on mount.
 * Returns { online, checking } so pages can show offline fallback UI.
 * Caches the result for 30 seconds across hook instances on the same page load.
 */

let _cache: { online: boolean; ts: number } | null = null;
const TTL = 30_000;

export function useBackend() {
  const [online, setOnline] = useState<boolean | null>(_cache && Date.now() - _cache.ts < TTL ? _cache.online : null);

  useEffect(() => {
    if (_cache && Date.now() - _cache.ts < TTL) {
      setOnline(_cache.online);
      return;
    }
    fetch("/api/health", { signal: AbortSignal.timeout(4000) })
      .then((r) => {
        const ok = r.ok;
        _cache = { online: ok, ts: Date.now() };
        setOnline(ok);
      })
      .catch(() => {
        _cache = { online: false, ts: Date.now() };
        setOnline(false);
      });
  }, []);

  return { online: online ?? false, checking: online === null };
}
