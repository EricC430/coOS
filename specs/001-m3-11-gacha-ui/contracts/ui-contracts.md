# UI Component Contracts: M3.11 Gamification Gacha & Visual Studio

## 1. `GachaDrawButton`

```typescript
export interface GachaDrawButtonProps {
  userXp: number;
  cost?: number;                           // default: 100
  initialDrawHistory?: number[];           // past timestamps (ms) for sliding window
  initialPoolMode?: GachaPoolMode;         // "curated" | "hybrid"
  userPoolItems?: VisualItem[];
  onDraw: (poolMode: GachaPoolMode) => Promise<DrawResponse>;
  onItemAcquired?: (item: VisualItem) => void;
}
```

- **Invariants**:
  - `userXp < cost` → Button disabled, shows error text: `需要 100 XP（餘額不足）`.
  - `recentDraws >= 5` within 60 mins → Button disabled, shows cooldown text: `已達 1 小時上限（5/5）冷卻中`.
  - Draw success → Fires `GachaResultToast` with `data-defer-strategy="immediate"`.

---

## 2. `BackgroundGenerator`

```typescript
export interface BackgroundGeneratorProps {
  initialItem?: VisualItem | null;
  onGenerate: (prompt: string, style: BackgroundStyle) => Promise<VisualItem>;
  onSave: (item: VisualItem) => void;
}
```

- **Prompt Transformation**:
  - Dynamically synthesizes natural language descriptive sentence based on style template.
  - Zero comma tag dumps (`8k, masterpiece`).
- **Gacha Pool Switch**:
  - Toggle `in_gacha_pool: true/false` directly modifies the item's eligibility in hybrid draw pool.

---

## 3. `ObjectGenerator`

```typescript
export interface ObjectGeneratorProps {
  initialItem?: VisualItem | null;
  onGenerate: (semanticFeatures: string, category: "badge" | "prop") => Promise<VisualItem>;
  onSave: (item: VisualItem) => void;
}
```

- **Prompt Transformation**:
  - Enforces centered subject and pure isolated transparent background.
- **Transparency Validation**:
  - Renders checkerboard background (`data-testid="transparency-checkerboard"`) to ensure zero background artifacts.

---

## 4. `VisualStudioCanvas`

```typescript
export interface VisualStudioCanvasProps {
  initialBackground?: VisualItem | null;
  initialLayers?: CanvasLayer[];
  inventoryObjects?: VisualItem[];
  availableBackgrounds?: VisualItem[];
  onHarmonize?: (request: HarmonizeRequest) => Promise<HarmonizeResult>;
  onApplyTheme?: (scene: CustomThemeScene) => void;
}
```

- **Non-destructive Staging**:
  - Clicking "✨ 放置（AI 融合）" updates `harmonizedResult` and switches to preview mode without mutating or flattening `layers`.
  - Clicking "返回編輯圖層" preserves all coordinates, scales, and rotations.
- **Fail-safe Fallback**:
  - If network throws or exceeds 10s, returns 2D canvas composition with `is_fallback: true` and `provider: "canvas_2d_fallback"`.

---

## 5. Psychological Gating Components

```typescript
// AchievementGrid: Zero-Leakage (FR-011)
export interface AchievementGridProps {
  items: VisualItem[];
  onSelectItem?: (item: VisualItem) => void;
}
// Unearned hidden items MUST NOT render any DOM node or placeholder.

// GachaPromotion: Anxiety Gate (FR-013)
export interface GachaPromotionProps {
  implicitState?: ImplicitUserState | null;
  onOpenGacha?: () => void;
}
// If implicitState.label in ["anxiety", "avoidance", "depression"], returns null.

// DrawChallengeButton: No XP Staking (FR-014)
export interface DrawChallengeButtonProps {
  onDrawChallenge: () => Promise<ZPDChallenge>;
  onAcceptChallenge?: (challenge: ZPDChallenge) => void;
}
// Zero stake / wager inputs, sliders, or XP risk.
```
