import React from "react";
import { ImplicitUserState } from "../types";

export interface GachaPromotionProps {
  implicitState?: ImplicitUserState | null;
  onOpenGacha?: () => void;
}

const SUPPRESSED_STATES = new Set(["anxiety", "avoidance", "depression"]);

/**
 * GachaPromotion: Complies with Constitution Rule 2 (RISK-09)
 * Anxiety-Gated Promotion Suppression:
 * When the user's inferred psychological state is anxiety, avoidance, or depression,
 * actively suppress promotional banners to prevent psychological distress or impulsive gambling.
 */
export const GachaPromotion: React.FC<GachaPromotionProps> = ({
  implicitState,
  onOpenGacha,
}) => {
  if (implicitState?.label && SUPPRESSED_STATES.has(implicitState.label)) {
    return null;
  }

  return (
    <div
      data-testid="gacha-promotion-banner"
      className="flex items-center justify-between rounded-xl border border-indigo-500/30 bg-gradient-to-r from-indigo-950/60 via-purple-950/60 to-slate-900/60 p-4 text-white shadow-lg backdrop-blur-sm"
    >
      <div className="flex items-center gap-3">
        <span className="text-2xl">✨</span>
        <div>
          <h4 className="text-sm font-bold text-indigo-200">
            今天手感絕佳！
          </h4>
          <p className="text-xs text-slate-300">
            要不要來抽張新背景或裝飾物，為個人專屬空間增添新靈感？
          </p>
        </div>
      </div>

      {onOpenGacha && (
        <button
          onClick={onOpenGacha}
          className="rounded-lg bg-indigo-600 px-3.5 py-1.5 text-xs font-bold text-white shadow-md hover:bg-indigo-500 active:scale-95 transition"
        >
          前往抽卡
        </button>
      )}
    </div>
  );
};
