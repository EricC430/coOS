import React from "react";
import { VisualItem, ItemRarity } from "../types";

export interface GachaResultToastProps {
  item: VisualItem;
  onClose?: () => void;
}

const RARITY_STYLES: Record<
  ItemRarity,
  { label: string; border: string; glow: string; badgeBg: string; text: string }
> = {
  common: {
    label: "普通",
    border: "border-slate-500",
    glow: "shadow-slate-500/20",
    badgeBg: "bg-slate-700 text-slate-200",
    text: "text-slate-200",
  },
  rare: {
    label: "稀有",
    border: "border-cyan-500",
    glow: "shadow-cyan-500/40 shadow-lg",
    badgeBg: "bg-cyan-900/80 text-cyan-200 border border-cyan-400",
    text: "text-cyan-300",
  },
  epic: {
    label: "史詩",
    border: "border-purple-500",
    glow: "shadow-purple-500/50 shadow-xl",
    badgeBg: "bg-purple-900/80 text-purple-200 border border-purple-400",
    text: "text-purple-300",
  },
  legendary: {
    label: "傳奇",
    border: "border-amber-400",
    glow: "shadow-amber-400/60 shadow-2xl ring-2 ring-amber-300/50",
    badgeBg: "bg-amber-900/90 text-amber-200 border border-amber-300 font-bold",
    text: "text-amber-300 font-extrabold",
  },
};

export const GachaResultToast: React.FC<GachaResultToastProps> = ({
  item,
  onClose,
}) => {
  const styling = RARITY_STYLES[item.rarity] || RARITY_STYLES.common;

  return (
    <div
      data-testid="gacha-result-toast"
      data-defer-strategy="immediate"
      className={`fixed bottom-6 right-6 z-50 flex max-w-md items-center gap-4 rounded-xl border bg-slate-900/95 p-4 text-white backdrop-blur-md transition-all duration-300 ${styling.border} ${styling.glow}`}
    >
      <div className="relative flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-slate-800/80 border border-slate-700">
        <img
          src={item.image_url}
          alt={item.name}
          className="max-h-full max-w-full object-contain"
        />
        {item.is_user_generated && (
          <span className="absolute top-1 left-1 rounded bg-indigo-600/90 px-1 text-[9px] font-semibold text-white">
            自創
          </span>
        )}
      </div>

      <div className="flex flex-1 flex-col">
        <div className="flex items-center gap-2">
          <span className={`text-base font-bold ${styling.text}`}>
            {item.name}
          </span>
          <span className={`rounded px-1.5 py-0.5 text-xs ${styling.badgeBg}`}>
            {styling.label}
          </span>
        </div>
        <p className="mt-1 line-clamp-2 text-xs text-slate-300">
          {item.description}
        </p>
        <span className="mt-1 text-[10px] text-slate-400">
          {item.category === "background" ? "背景圖片" : "透明物件"}
        </span>
      </div>

      {onClose && (
        <button
          onClick={onClose}
          className="ml-2 rounded-lg p-1 text-slate-400 hover:bg-slate-800 hover:text-white"
          aria-label="關閉"
        >
          ✕
        </button>
      )}
    </div>
  );
};
