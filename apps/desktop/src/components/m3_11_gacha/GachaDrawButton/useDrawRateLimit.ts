import { useState, useCallback, useMemo } from "react";
import { GachaPoolMode, DrawRateLimitState } from "../types";

const ONE_HOUR_MS = 60 * 60 * 1000;
const MAX_DRAWS_ALLOWED = 5;

export interface UseDrawRateLimitOptions {
  initialHistory?: number[];
  initialPoolMode?: GachaPoolMode;
}

export function useDrawRateLimit(options: UseDrawRateLimitOptions = {}) {
  const [drawHistory, setDrawHistory] = useState<number[]>(
    () => options.initialHistory || []
  );
  const [currentPoolMode, setCurrentPoolMode] = useState<GachaPoolMode>(
    options.initialPoolMode || "curated"
  );

  const cleanHistory = useMemo(() => {
    const now = Date.now();
    return drawHistory.filter((timestamp) => now - timestamp < ONE_HOUR_MS);
  }, [drawHistory]);

  const drawCountInLastHour = cleanHistory.length;
  const isCoolingDown = drawCountInLastHour >= MAX_DRAWS_ALLOWED;

  const cooldownRemainingMs = useMemo(() => {
    if (!isCoolingDown || cleanHistory.length === 0) return 0;
    const now = Date.now();
    const oldestInWindow = Math.min(...cleanHistory);
    const expireTime = oldestInWindow + ONE_HOUR_MS;
    return Math.max(0, expireTime - now);
  }, [isCoolingDown, cleanHistory]);

  const recordDraw = useCallback(() => {
    const now = Date.now();
    setDrawHistory((prev) => [...prev, now]);
  }, []);

  const togglePoolMode = useCallback(() => {
    setCurrentPoolMode((prev) => (prev === "curated" ? "hybrid" : "curated"));
  }, []);

  const state: DrawRateLimitState = {
    drawHistory: cleanHistory,
    isCoolingDown,
    drawCountInLastHour,
    maxDrawsAllowed: MAX_DRAWS_ALLOWED,
    cooldownRemainingMs,
    currentPoolMode,
  };

  return {
    state,
    recordDraw,
    currentPoolMode,
    setCurrentPoolMode,
    togglePoolMode,
  };
}
