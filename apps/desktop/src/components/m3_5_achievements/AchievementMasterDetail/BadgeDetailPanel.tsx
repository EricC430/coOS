/**
 * M3.5.1 -- Badge detail panel (right side of master-detail)
 */

import React from "react";
import type { BadgeItem } from "../BadgeSlot";

interface Props {
  item: BadgeItem;
}

export function BadgeDetailPanel({ item }: Props) {
  return (
    <div data-testid="badge-detail-panel" className="p-4 space-y-3">
      <div className="flex items-center gap-3">
        {item.image_url ? (
          <img src={item.image_url} alt={item.name} className="w-16 h-16 object-contain" />
        ) : (
          <div className="text-5xl">🎖</div>
        )}
        <div>
          <div className="font-semibold text-lg">{item.name ?? "—"}</div>
          <div className="text-xs text-gray-400 capitalize">{item.rarity}</div>
        </div>
      </div>

      {item.description && (
        <p className="text-sm text-gray-600">{item.description}</p>
      )}

      {item.acquired_at && (
        <div className="text-xs text-gray-400">取得日期：{item.acquired_at}</div>
      )}

      <div
        data-testid="badge-unlock-condition"
        className="text-xs text-indigo-600 bg-indigo-50 rounded p-2"
      >
        {item.unlock_condition ?? "完成特定目標解鎖"}
      </div>
    </div>
  );
}
