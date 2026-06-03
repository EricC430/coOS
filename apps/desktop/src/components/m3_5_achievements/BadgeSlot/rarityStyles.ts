/**
 * M3.5.2 -- Rarity style definitions
 * [R09 §HAIA] Visual differentiation reinforces ownership feel
 */

export type Rarity = "common" | "rare" | "epic" | "legendary";

export const rarityConfig: Record<Rarity, { className: string; label: string }> = {
  common: { className: "rarity-common border-2 border-gray-300", label: "普通" },
  rare: { className: "rarity-rare border-2 border-blue-400 shadow-blue-200 shadow-md", label: "稀有" },
  epic: { className: "rarity-epic border-2 border-purple-400 shadow-purple-200 shadow-md animate-pulse", label: "史詩" },
  legendary: { className: "rarity-legendary border-2 border-yellow-400 shadow-yellow-200 shadow-lg", label: "傳說" },
};
