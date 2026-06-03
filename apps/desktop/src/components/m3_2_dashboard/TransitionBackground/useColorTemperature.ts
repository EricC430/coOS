/**
 * M3.2.2.2 -- Color temperature interpolation
 * [R08 SS1] 500ms gradient avoids visual shock on role switch.
 * Uses CSS custom properties so framer-motion can tween them.
 */

import { useEffect } from "react";

export interface ThemePalette {
  primary: string;
  secondary?: string;
}

function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  const full = clean.length === 3
    ? clean.split("").map((c) => c + c).join("")
    : clean;
  const num = parseInt(full, 16);
  return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
}

function lerpColor(from: string, to: string, t: number): string {
  const [r1, g1, b1] = hexToRgb(from);
  const [r2, g2, b2] = hexToRgb(to);
  const r = Math.round(r1 + (r2 - r1) * t);
  const g = Math.round(g1 + (g2 - g1) * t);
  const b = Math.round(b1 + (b2 - b1) * t);
  return `rgb(${r},${g},${b})`;
}

export function useColorTemperature(
  from: ThemePalette,
  to: ThemePalette,
  durationMs = 500,
  onComplete?: () => void
) {
  useEffect(() => {
    const start = performance.now();
    let raf = 0;

    function tick(now: number) {
      const t = Math.min((now - start) / durationMs, 1);
      const color = lerpColor(from.primary, to.primary, t);
      document.documentElement.style.setProperty("--role-primary", color);
      if (t < 1) {
        raf = requestAnimationFrame(tick);
      } else {
        onComplete?.();
      }
    }

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [to.primary, durationMs]);
}
