/**
 * M3.2.5 -- Widget Layout Hook
 *
 * Persists per-role widget layout configuration to localStorage.
 * Supports ordering, add, remove, and custom title.
 *
 * [FIX-01] Shared widget grid for Dashboard, Promises, Goal cards.
 */

export type WidgetType =
  | "heatmap_365"
  | "monthly_consistency"
  | "weekly_mood"
  | "weekly_chat_count"
  | "custom_chart";

export interface WidgetConfig {
  id: string;           // Unique instance id (uuid-like)
  type: WidgetType;
  title: string;
  filterParams?: Record<string, unknown>;  // For custom_chart
}

export const WIDGET_REGISTRY: Record<WidgetType, { label: string; description: string }> = {
  heatmap_365:         { label: "365 天一致性紀錄", description: "過去一年每日活躍度熱力圖" },
  monthly_consistency: { label: "當月一致性紀錄",   description: "本月每日活躍度條狀圖" },
  weekly_mood:         { label: "當週心情起伏",     description: "本週情緒波動折線圖" },
  weekly_chat_count:   { label: "當週聊聊次數",     description: "本週與各專家對話次數" },
  custom_chart:        { label: "自訂篩選圖表",     description: "自訂日期範圍與指標的視覺化" },
};

const DEFAULT_LAYOUT: WidgetConfig[] = [
  { id: "w_heatmap_365", type: "heatmap_365", title: "365 天一致性紀錄" },
];

function storageKey(roleId: string) {
  return `coos:widgetLayout:${roleId}`;
}

export function loadWidgetLayout(roleId: string): WidgetConfig[] {
  try {
    const raw = localStorage.getItem(storageKey(roleId));
    if (!raw) return DEFAULT_LAYOUT;
    const parsed = JSON.parse(raw) as WidgetConfig[];
    if (!Array.isArray(parsed) || parsed.length === 0) return DEFAULT_LAYOUT;
    return parsed;
  } catch {
    return DEFAULT_LAYOUT;
  }
}

export function saveWidgetLayout(roleId: string, layout: WidgetConfig[]): void {
  try {
    localStorage.setItem(storageKey(roleId), JSON.stringify(layout));
  } catch { /* non-fatal */ }
}

let _widgetCounter = Date.now();
export function newWidgetId(): string {
  return `w_${++_widgetCounter}`;
}
