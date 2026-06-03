/**
 * M3.2.2 -- Role Transition Background Engine
 *
 * SPEC: docs/modules/M3_2_role_dashboard_SPEC.md SS7.2
 * [R08 SS1] 500ms color gradient avoids visual shock, supports cognitive reset
 * Respects prefers-reduced-motion for accessibility
 */

import React, { useEffect, useRef } from "react";
import { useColorTemperature, type ThemePalette } from "./useColorTemperature";

interface Props {
  roleId: string;
  palette: ThemePalette;
  isTransitioning?: boolean;
  onTransitionEnd?: () => void;
}

const DEFAULT_PALETTE: ThemePalette = { primary: "#6366f1" };

export function TransitionBackground({
  palette,
  isTransitioning = false,
  onTransitionEnd,
}: Props) {
  const prevPalette = useRef<ThemePalette>(palette);
  const reducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  useColorTemperature(
    prevPalette.current,
    palette,
    reducedMotion ? 0 : 500,
    () => {
      prevPalette.current = palette;
      onTransitionEnd?.();
    }
  );

  return (
    <div
      data-testid="transition-background"
      className="fixed inset-0 -z-10 transition-colors duration-500"
      style={{
        background: `linear-gradient(135deg, var(--role-primary, ${palette.primary})22 0%, transparent 60%)`,
      }}
    >
      {isTransitioning && (
        <div
          data-testid="ambient-glow"
          className="absolute inset-0"
          style={{ backdropFilter: "blur(4px)", opacity: 0.5 }}
        />
      )}
    </div>
  );
}
