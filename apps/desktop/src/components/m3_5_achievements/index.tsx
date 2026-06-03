/**
 * M3.5 -- Achievement Display Module
 *
 * SPEC: docs/modules/M3_5_achievement_display_SPEC.md
 * Research: [R09 §HAIA] [R01 §Dropout buffer]
 * Risk: RISK-09 -- NO Gacha entry in this module; buttons disabled as placeholder
 */

import React from "react";
import { useQuery } from "@tanstack/react-query";
import { useCoOSStore } from "../../stores/m3_1_global_store";
import { AchievementMasterDetail } from "./AchievementMasterDetail";
import type { BadgeItem } from "./BadgeSlot";

async function fetchCollections(): Promise<BadgeItem[]> {
  const res = await fetch("/api/m6_5/user_collections");
  if (!res.ok) return [];
  return res.json();
}

async function fetchDictionary(): Promise<BadgeItem[]> {
  const res = await fetch("/api/m6_5/items_dictionary");
  if (!res.ok) return [];
  return res.json();
}

export function AchievementDisplay() {
  const xpBalance = useCoOSStore((s) => s.xpBalance);
  const { data: collections = [] } = useQuery({ queryKey: ["user_collections"], queryFn: fetchCollections });
  const { data: dictionary = [] } = useQuery({ queryKey: ["items_dictionary"], queryFn: fetchDictionary });

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="font-semibold">Collection</h2>
        <div className="flex items-center gap-3">
          <span className="font-bold text-indigo-600">XP {xpBalance}</span>
          {/* [RISK-09] Gacha buttons disabled placeholder -- unlocked in M3.11 */}
          <button
            disabled
            title="解鎖進階功能後開放"
            className="px-2 py-1 text-xs rounded border border-gray-200 text-gray-300 cursor-not-allowed"
          >
            抽背景
          </button>
          <button
            disabled
            title="解鎖進階功能後開放"
            className="px-2 py-1 text-xs rounded border border-gray-200 text-gray-300 cursor-not-allowed"
          >
            抽物件
          </button>
        </div>
      </div>

      {/* Master-Detail */}
      <div className="flex-1 overflow-hidden">
        <AchievementMasterDetail
          collections={collections}
          dictionary={dictionary}
        />
      </div>

      <div className="px-4 py-2 text-xs text-gray-400 text-center border-t">
        收集 XP 可能可以抽取紀念徽章
      </div>
    </div>
  );
}
