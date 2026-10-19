import React from "react";
import { VisualItem } from "../types";

export interface AchievementGridProps {
  items: VisualItem[];
  onSelectItem?: (item: VisualItem) => void;
}

/**
 * AchievementGrid: Complies with Constitution Rule 2 and M3.11.3 (Zero Leakage)
 * Unearned hidden achievements (item.hidden && !item.unlocked_at) MUST NEVER produce
 * any DOM node, placeholder, or '???' in the UI.
 */
export const AchievementGrid: React.FC<AchievementGridProps> = ({
  items,
  onSelectItem,
}) => {
  // STRICT FILTER: Zero UI footprint for unearned hidden items
  const visibleItems = items.filter((item) => {
    if (item.hidden && !item.unlocked_at) {
      return false;
    }
    return true;
  });

  return (
    <div
      data-testid="achievement-grid"
      className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4"
    >
      {visibleItems.map((item) => (
        <div
          key={item.id}
          data-testid="achievement-item"
          onClick={() => onSelectItem && onSelectItem(item)}
          className="group relative flex flex-col items-center rounded-xl border border-slate-700 bg-slate-800/60 p-3 text-center transition hover:border-indigo-500 hover:bg-slate-800 cursor-pointer"
        >
          <div className="relative mb-2 flex h-16 w-16 items-center justify-center overflow-hidden rounded-lg bg-slate-900/50">
            <img
              src={item.image_url}
              alt={item.name}
              className="max-h-full max-w-full object-contain group-hover:scale-105 transition"
            />
          </div>
          <span className="text-xs font-semibold text-slate-200 line-clamp-1">
            {item.name}
          </span>
          <span className="mt-1 text-[10px] text-slate-400 capitalize">
            {item.rarity}
          </span>
        </div>
      ))}
    </div>
  );
};
