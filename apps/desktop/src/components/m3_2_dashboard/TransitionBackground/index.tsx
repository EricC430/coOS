/**
 * M3.2.2 -- Role Transition Background Engine
 *
 * SPEC: docs/modules/M3_2_role_dashboard_SPEC.md SS7.2
 * [R08 SS1] 500ms color gradient avoids visual shock, supports cognitive reset
 * Respects prefers-reduced-motion for accessibility
 *
 * Redesign: Warm therapeutic-alliance themed background with
 * subtle concentric circle ripples and ambient glow.
 */

import { useRef } from "react";
import { useColorTemperature, type ThemePalette } from "./useColorTemperature";

interface Props {
  roleId: string;
  palette: ThemePalette;
  isTransitioning?: boolean;
  onTransitionEnd?: () => void;
}

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
    <div className="app-background" data-testid="transition-background">
      {/* Role-specific ambient glow */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse 50% 50% at 50% 80%, ${palette.primary}15 0%, transparent 70%)`,
          transition: "background 0.6s ease",
          pointerEvents: "none",
        }}
      />

      {/* Transitioning blur overlay */}
      {isTransitioning && (
        <div
          data-testid="ambient-glow"
          style={{
            position: "absolute",
            inset: 0,
            backdropFilter: "blur(4px)",
            opacity: 0.5,
          }}
        />
      )}
    </div>
  );
}
