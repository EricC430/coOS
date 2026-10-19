/**
 * M3.11 Gamification Gacha & Visual Studio Types
 * Complies with Constitution Rule 1 (Privacy), Rule 2 (Psychological Invariants) and Data Model
 */

export type ItemRarity = "common" | "rare" | "epic" | "legendary";
export type ItemCategory = "background" | "badge" | "theme" | "prop";

export interface VisualItem {
  id: string;                      // 唯一識別碼，例如 "bg_cyber_study" 或 "prop_zen_plant"
  name: string;                    // 顯示名稱
  description: string;             // 描述文字
  category: ItemCategory;          // 物品類別
  rarity: ItemRarity;              // 稀有度等級
  image_url: string;               // 圖片資料（URL / SVG / Base64 Data URL）
  has_transparency: boolean;       // 是否具備透明 Alpha 通道（物體為 true，背景為 false）
  scene_description?: string;      // 背景專用：背景場景描述
  semantic_features?: string;      // 物件專用：物件語意特徵
  is_user_generated: boolean;      // 是否為使用者自訂生成資產（預設 false 為系統官方）
  in_gacha_pool: boolean;          // 是否已投入抽獎池供抽取（自訂資產可勾選）
  hidden: boolean;                 // 是否為隱藏成就（解鎖前絕無 UI 狀態）
  unlocked_at?: string | null;     // ISO 8601 時間字串；null 代表未解鎖
}

export interface CanvasLayer {
  id: string;                      // 圖層唯一識別碼（UUID）
  item_id: string;                 // 對應之 VisualItem ID
  name: string;                    // 物體名稱
  image_url: string;               // 物體透明圖片路徑
  semantic_features?: string;      // 該物體之語意特徵（供圖生圖融合提示使用）
  x: number;                       // 畫布 X 坐標（像素）
  y: number;                       // 畫布 Y 坐標（像素）
  scale: number;                   // 縮放比例（0.2 ~ 3.0，預設 1.0）
  rotation: number;                // 旋轉角度（0 ~ 360 度）
  zIndex: number;                  // 堆疊層次（數字越大越在上層）
}

export interface CanvasState {
  background: VisualItem | null;   // 當前選用之背景底圖
  layers: CanvasLayer[];           // 畫布上疊加之物體圖層陣列（非破壞性保留）
  selectedLayerId: string | null;  // 當前選取中之圖層 ID
  canvasWidth: number;             // 畫布寬度（預設 800px）
  canvasHeight: number;            // 畫布高度（預設 500px）
  harmonized_preview_url?: string | null; // AI 融合後的成果預覽圖
  is_preview_mode: boolean;        // 是否處於融合成果預覽檢視模式
}

export interface CustomThemeScene {
  id: string;                      // 場景唯一 ID
  name: string;                    // 場景名稱
  created_at: string;              // 建立時間 (ISO 8601)
  canvas_state: CanvasState;       // 當時畫布圖層與底圖設定
  final_image_url: string;         // AI 融合或 2D 備援之最終高清圖
  is_active_theme?: boolean;       // 是否為目前桌面套用之主背景
}

export interface HarmonizeRequest {
  base64_draft: string;            // 2D 畫布底稿之 Base64 圖片
  scene_description?: string;      // 背景場景描述
  objects_summary?: string;        // 各物體語意特徵摘要
}

export interface HarmonizeResult {
  image_url: string;               // 融合完成之影像 URL 或 Base64
  is_fallback: boolean;            // 是否為網路異常時的 2D 畫布自動降級產物
  provider: "pollinations" | "huggingface_free" | "canvas_2d_fallback";
}

export type GachaPoolMode = "curated" | "hybrid";

export interface DrawRateLimitState {
  drawHistory: number[];           // 過去 60 分鐘內每次抽獎時間戳記 (Epoch ms)
  isCoolingDown: boolean;          // 當前是否處於冷卻鎖定 (count >= 5)
  drawCountInLastHour: number;     // 過去 1 小時內的抽獎次數
  maxDrawsAllowed: number;         // 允許最大次數 (固定為 5)
  cooldownRemainingMs: number;     // 距離最舊一次抽獎超過 1 小時還剩餘的毫秒數
  currentPoolMode: GachaPoolMode;  // 當前選擇的獎池模式（官方精選 / 自創混合）
}

export interface ImplicitUserState {
  label: "anxiety" | "avoidance" | "depression" | "neutral" | "flow" | string;
  confidence?: number;
}

export interface DrawResponse {
  success: boolean;
  item?: VisualItem;
  cost: number;
  remaining_xp: number;
  error?: string;
}

export interface ZPDChallenge {
  id: string;
  title: string;
  difficulty: "just-manageable" | "stretch";
  xp_reward: number;
  estimated_minutes: number;
  description: string;
}

export interface HiddenAchievementEvent {
  type: "HIDDEN_ACHIEVEMENT_UNLOCKED";
  item: VisualItem;
}
