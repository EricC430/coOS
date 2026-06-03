/**
 * M3.5.1 -- Achievement Master-Detail Layout
 */

import React, { useState } from "react";
import { AchievementGrid } from "./AchievementGrid";
import { BadgeDetailPanel } from "./BadgeDetailPanel";
import type { BadgeItem } from "../BadgeSlot";

interface Props {
  collections: BadgeItem[];
  dictionary?: BadgeItem[];
}

export function AchievementMasterDetail({ collections, dictionary }: Props) {
  const [selected, setSelected] = useState<BadgeItem | null>(
    collections[0] ?? null
  );

  return (
    <div className="flex h-full">
      {/* Left: grid */}
      <div className="flex-1 overflow-y-auto">
        <AchievementGrid
          collections={collections}
          dictionary={dictionary}
          onSelect={setSelected}
        />
      </div>

      {/* Right: detail */}
      {selected && (
        <div className="w-56 border-l flex-shrink-0">
          <BadgeDetailPanel item={selected} />
        </div>
      )}
    </div>
  );
}
