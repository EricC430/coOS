/**
 * M3.5.2 -- Badge Slot
 * Locked slots show question-mark only -- never reveal conditions
 * Anti-pattern: do NOT show unlock conditions for locked badges
 */

import React, { useState } from "react";
import { rarityConfig, type Rarity } from "./rarityStyles";

export interface BadgeItem {
  id: string;
  name?: string;
  rarity: Rarity;
  image_url?: string;
  acquired_at?: string;
  description?: string;
  unlock_condition?: string;
}

interface Props {
  item: BadgeItem;
  unlocked: boolean;
  onClick?: () => void;
}

export function BadgeSlot({ item, unlocked, onClick }: Props) {
  const [imgError, setImgError] = useState(false);
  const rarity = rarityConfig[item.rarity] ?? rarityConfig.common;

  if (!unlocked) {
    return (
      <div
        data-testid="badge-slot-locked"
        className={`locked w-12 h-12 rounded-lg flex items-center justify-center bg-gray-100 ${rarity.className} opacity-40 cursor-not-allowed`}
      >
        <span className="text-gray-400 text-xl">?</span>
      </div>
    );
  }

  return (
    <div
      data-testid="badge-slot"
      className={`w-12 h-12 rounded-lg flex items-center justify-center cursor-pointer hover:scale-110 transition-transform ${rarity.className}`}
      data-badge-frame={rarity.className}
      onClick={onClick}
    >
      <div data-testid="badge-frame" className={rarity.className.split(" ").find((c) => c.startsWith("rarity-"))}>
        {item.image_url && !imgError ? (
          <img
            src={item.image_url}
            alt={item.name}
            className="w-10 h-10 object-contain rounded"
            onError={() => setImgError(true)}
          />
        ) : (
          <div data-testid="badge-image-fallback" className="text-2xl">
            🎖
          </div>
        )}
      </div>
    </div>
  );
}
