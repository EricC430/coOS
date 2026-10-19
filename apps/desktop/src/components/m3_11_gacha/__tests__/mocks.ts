import { VisualItem, DrawResponse, ZPDChallenge, HarmonizeResult } from "../types";
import { PRESET_BACKGROUNDS } from "../presetBackgrounds";
import { PRESET_OBJECTS } from "../presetObjects";

export const MOCK_USER_ITEMS: VisualItem[] = [
  ...PRESET_BACKGROUNDS.slice(0, 2),
  ...PRESET_OBJECTS.slice(0, 3),
];

export const MOCK_HIDDEN_ACHIEVEMENT: VisualItem = {
  id: "ach_quantum_leap",
  name: "量子躍遷隱藏榮譽",
  description: "在連續 3 天深夜無畏心流狀態下完成超越自我的架構突破。",
  category: "badge",
  rarity: "legendary",
  image_url: "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><circle cx='80' cy='80' r='50' fill='%239b59b6'/></svg>",
  has_transparency: true,
  is_user_generated: false,
  in_gacha_pool: false,
  hidden: true,
  unlocked_at: null,
};

export const MOCK_UNLOCKED_HIDDEN_ACHIEVEMENT: VisualItem = {
  ...MOCK_HIDDEN_ACHIEVEMENT,
  unlocked_at: "2026-10-19T20:00:00.000Z",
};

export const MOCK_ZPD_CHALLENGE: ZPDChallenge = {
  id: "zpd_task_042",
  title: "探索 Rust FFI 零拷貝邊界：非同步通道對接",
  difficulty: "just-manageable",
  xp_reward: 250,
  estimated_minutes: 25,
  description: "此挑戰基於你當前的能力前沿（ZPD），專注於記憶體安全性與並行佇列，自由探索無任何損失機制。",
};

/**
 * Mock Gacha draw helper
 */
export function mockGachaDraw(
  currentXp: number,
  poolMode: "curated" | "hybrid" = "curated",
  userPool: VisualItem[] = []
): DrawResponse {
  if (currentXp < 100) {
    return {
      success: false,
      cost: 0,
      remaining_xp: currentXp,
      error: "需要 100 XP（餘額不足）",
    };
  }

  const pool =
    poolMode === "hybrid" && userPool.length > 0
      ? [...PRESET_BACKGROUNDS, ...PRESET_OBJECTS, ...userPool]
      : [...PRESET_BACKGROUNDS, ...PRESET_OBJECTS];

  const picked = pool[Math.floor(Math.random() * pool.length)];

  return {
    success: true,
    item: picked,
    cost: 100,
    remaining_xp: currentXp - 100,
  };
}

/**
 * Mock free Image Harmonizer (Pollinations / 2D Fallback)
 */
export async function mockHarmonize(
  draftBase64: string,
  simulateNetworkFailure = false
): Promise<HarmonizeResult> {
  if (simulateNetworkFailure) {
    return {
      image_url: draftBase64,
      is_fallback: true,
      provider: "canvas_2d_fallback",
    };
  }

  return {
    image_url: `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="800" height="500"><rect width="800" height="500" fill="%232c3e50"/><text x="400" y="250" fill="%23ffffff" text-anchor="middle">AI Harmonized Scene</text></svg>`,
    is_fallback: false,
    provider: "pollinations",
  };
}

/**
 * Mock WebSocket for Hidden Achievement Events
 */
export class MockWebSocketClient {
  private listeners: ((event: { data: string }) => void)[] = [];

  addEventListener(_type: string, callback: (event: { data: string }) => void) {
    this.listeners.push(callback);
  }

  removeEventListener(_type: string, callback: (event: { data: string }) => void) {
    this.listeners = this.listeners.filter((cb) => cb !== callback);
  }

  emit(data: any) {
    const payload = { data: JSON.stringify(data) };
    this.listeners.forEach((cb) => cb(payload));
  }
}
