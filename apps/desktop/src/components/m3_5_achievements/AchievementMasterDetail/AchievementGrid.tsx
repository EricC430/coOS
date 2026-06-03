/**
 * M3.5.1 -- Achievement Grid (left panel)
 * [R09 §HAIA] Visible collection strengthens attachment
 * Anti-pattern: NEVER place Gacha buttons here (RISK-09)
 */

import React from "react";
import { BadgeSlot, type BadgeItem } from "../BadgeSlot";

interface Props {
  collections: BadgeItem[];
  dictionary?: BadgeItem[];
  onSelect: (item: BadgeItem) => void;
}

export function AchievementGrid({ collections, dictionary = [], onSelect }: Props) {
  const unlockedIds = new Set(collections.map((c) => c.id));

  // Show unlocked + locked (from dictionary) -- locked show ?
  const allItems: Array<{ item: BadgeItem; unlocked: boolean }> = [
    ...collections.map((item) => ({ item, unlocked: true })),
    ...dictionary
      .filter((item) => !unlockedIds.has(item.id))
      .map((item) => ({ item, unlocked: false })),
  ];

  if (allItems.length === 0) {
    return (
      <div className="text-center text-gray-400 text-sm py-8">
        完成第一個反思草稿即可解鎖你的首個徽章
      </div>
    );
  }

  return (
    <div className="grid grid-cols-6 gap-2 p-2">
      {allItems.map(({ item, unlocked }) => (
        <BadgeSlot
          key={item.id}
          item={item}
          unlocked={unlocked}
          onClick={unlocked ? () => onSelect(item) : undefined}
        />
      ))}
    </div>
  );
}
