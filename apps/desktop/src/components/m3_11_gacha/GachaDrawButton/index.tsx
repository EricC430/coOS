import React, { useState } from "react";
import { VisualItem, DrawResponse, GachaPoolMode } from "../types";
import { useDrawRateLimit } from "./useDrawRateLimit";
import { GachaResultToast } from "./GachaResultToast";
import { logGachaEvent } from "../telemetry";

export interface GachaDrawButtonProps {
  userXp: number;
  cost?: number;
  initialDrawHistory?: number[];
  initialPoolMode?: GachaPoolMode;
  userPoolItems?: VisualItem[];
  onDraw: (poolMode: GachaPoolMode) => Promise<DrawResponse>;
  onItemAcquired?: (item: VisualItem) => void;
}

export const GachaDrawButton: React.FC<GachaDrawButtonProps> = ({
  userXp,
  cost = 100,
  initialDrawHistory,
  initialPoolMode,
  userPoolItems = [],
  onDraw,
  onItemAcquired,
}) => {
  const { state: rateLimitState, recordDraw, currentPoolMode, togglePoolMode } =
    useDrawRateLimit({
      initialHistory: initialDrawHistory,
      initialPoolMode,
    });

  const [isLoading, setIsLoading] = useState(false);
  const [latestItem, setLatestItem] = useState<VisualItem | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isXpInsufficient = userXp < cost;
  const isCooldown = rateLimitState.isCoolingDown;
  const isDisabled = isXpInsufficient || isCooldown || isLoading;

  const handleDrawClick = async () => {
    if (isDisabled) return;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const response = await onDraw(currentPoolMode);
      if (response.success && response.item) {
        recordDraw();
        setLatestItem(response.item);
        logGachaEvent("gacha_draw_success", {
          item_id: response.item.id,
          rarity: response.item.rarity,
          poolMode: currentPoolMode,
        });
        if (onItemAcquired) {
          onItemAcquired(response.item);
        }
      } else {
        setErrorMessage(response.error || "抽獎失敗，XP 未扣除");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "抽獎服務發生網路異常，XP 未扣除");
    } finally {
      setIsLoading(false);
    }
  };

  const poolModeLabel =
    currentPoolMode === "hybrid" ? "自創混合池" : "官方精選池";

  return (
    <div className="flex flex-col gap-3 rounded-xl border border-slate-700 bg-slate-800/80 p-4 text-white shadow-md">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold text-slate-300">
          目前獎池: {poolModeLabel}
        </span>
        <button
          onClick={togglePoolMode}
          className="text-xs text-indigo-400 underline hover:text-indigo-300"
        >
          {currentPoolMode === "curated"
            ? "切換為自創混合池"
            : "切換為精選獎池"}
        </button>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>單次抽獎: {cost} XP</span>
        <span>餘額: {userXp} XP</span>
      </div>

      <button
        onClick={handleDrawClick}
        disabled={isDisabled}
        aria-label="盲盒抽獎"
        className={`flex w-full items-center justify-center gap-2 rounded-lg py-2.5 px-4 font-bold transition-all ${
          isDisabled
            ? "cursor-not-allowed bg-slate-700 text-slate-500"
            : "bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-600/30 hover:brightness-110 active:scale-[0.98]"
        }`}
      >
        {isLoading ? (
          <span className="flex items-center gap-2">
            <svg
              className="h-4 w-4 animate-spin text-white"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8v8H4z"
              />
            </svg>
            開獎中...
          </span>
        ) : (
          <span>🎁 盲盒抽獎（{cost} XP）</span>
        )}
      </button>

      {/* Warning/Status feedback */}
      {isXpInsufficient && (
        <p className="text-center text-xs text-rose-400">
          需要 {cost} XP（餘額不足）
        </p>
      )}

      {isCooldown && (
        <p className="text-center text-xs text-amber-400">
          已達 1 小時上限（5/5）冷卻中（剩餘約{" "}
          {Math.ceil(rateLimitState.cooldownRemainingMs / 60000)} 分鐘）
        </p>
      )}

      {errorMessage && (
        <p className="text-center text-xs text-rose-400">{errorMessage}</p>
      )}

      {/* L1 Instant celebration toast */}
      {latestItem && (
        <GachaResultToast
          item={latestItem}
          onClose={() => setLatestItem(null)}
        />
      )}
    </div>
  );
};
