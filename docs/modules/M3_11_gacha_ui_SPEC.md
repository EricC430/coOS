# M3.11 — 遊戲化抽卡組件 (Gamification Gacha UI)

**標籤**:`[進階]`
**版本**:`1.0`
**最後更新**:2026-06-03

> **MVP 策略**：Phase 1~5 不動工。依賴 M4.11（ZPD 任務池）、M4.12（隱藏成就驗證）、M6.5（ACID 抽卡守門員），三者均為進階模組。需等 MVP 閉環後才可動工。

## 1. Purpose

提供三種不同觸發機制的遊戲化增強介面：(1) 用 XP 換取盲盒抽卡；(2) 程序化隨機挑戰抽取；(3) 隱藏成就的無預警驚喜解鎖——透過「變動比例增強」製造合理的多巴胺回饋，同時以焦慮門禁與 Defer 機制防範成癮風險。

> ⚠️ **M3.11.3 隱藏成就無 UI 狀態控制器是鐵律**：解鎖前任何介面都不得暗示「這個成就存在」。違反此原則即觸發 FOMO，破壞驚喜機制。

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R01 | §DDA 與 PCG 建構性基元 | M3.11.2「抽挑戰」按鈕的程序化任務生成：難度由 M4.11 ZPD 邊界動態決定，而非固定池 |
| R01 | §α-DPO Dropout 危機 | M3.11.1 XP 抽卡：使用者主動消費，不在挫敗狀態下推播（RISK-09 門禁） |
| R09 | §3.3 病態使用風險 Replika 案例 | M3.11.1 連續抽卡計數限制：1 小時內 ≥5 次 → 顯示冷卻提示（RISK-09） |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.1 `xpBalance` | `number` | `1200`（用於確認抽卡費用） |
| M6.5 `items_dictionary` (via API) | `Item[]` | 抽卡獎池物品 |
| M4.11 ZPD 任務池 (via API) | `ZPDTask { text, difficulty, xp_reward }` | `{ text: "實作 K8s Ingress", difficulty: "stretch" }` |
| M4.12 WebSocket `HIDDEN_ACHIEVEMENT_UNLOCKED` | `{ achievement_id, name, description }` | `{ achievement_id: "ha_001", name: "深夜衝刺者" }` |
| M4.8 當前隱性狀態（焦慮門禁） | `{ label: string, confidence: number }` | `{ label: "anxiety", confidence: 0.85 }` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `POST /api/m6_5/draw_card` | `{ user_id, cost_xp }` | `{ cost_xp: 100 }` |
| `POST /api/m4_11/draw_challenge` | `{ role_id, current_zpd_zone }` | 抽取一個 ZPD 挑戰任務 |
| M6.5 `user_collections` (後端寫入) | — | 抽到的物品由後端 ACID 交易寫入，前端只接收結果 |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.11", event: "gacha_draw", item_id, rarity }` | 抽卡結果觀測 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M3.5** (成就展示)：M3.11 抽到的徽章／背景圖以 M3.5 的徽章槽位佈局為基礎展示，不重新發明 Grid
- **M4.11** (ZPD 任務池生成器)：M3.11.2「抽挑戰」的任務來源
- **M4.12** (隱藏成就驗證引擎)：M3.11.3 / M3.11.4 的觸發來源（後端驗證 → WebSocket 推送）
- **M6.5** (遊戲化交易引擎)：執行「扣 XP → 隨機權重抽取 → ACID 寫入」的後端守門員
- **M4.8** (隱性狀態推論，進階)：焦慮狀態門禁（RISK-09）

### 下游 (誰依賴我)

- **M3.5** (成就展示)：新解鎖物品出現在 M3.5 的收藏庫

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-04** | Gacha 結果若走 Defer 延遲 30 分鐘後才顯示，使用者失去因果連結 → 變動比例增強失效 | M3.11.1 抽卡結果屬 **L1 即時慶祝**（使用者主動觸發），**不經 M3.9 Defer**，直接顯示 Toast + 開獎動畫 |
| **RISK-09** | 焦慮狀態下系統主動推播 Gacha 邀請 → 賭博式增強複合焦慮 → 病態使用 | (1) 系統主動推播的 Gacha 邀請：M4.8 偵測焦慮時絕對不送；(2) 使用者主動點擊：顯示柔性提示但不阻擋 |
| **RISK-07** | 使用者對 ZPD 邊緣任務質押 XP 失敗 → 複合挫敗 | M3.11.2「抽挑戰」不支援 XP 質押；質押功能限定在 M3.7.8 且後端 M4.13 有成功率門禁 |

## 6. Acceptance Criteria

```typescript
// tests/m3_11/gacha_ui.test.ts

describe("M3.11.1 變動比例盲盒抽卡介面", () => {
  it("[RISK-04] 抽卡結果立即顯示 Toast，不等斷點", async () => {
    const drawSpy = vi.fn().mockResolvedValue({ item: mockItem, rarity: "rare" });
    render(<GachaDrawButton onDraw={drawSpy} xpBalance={500} />);
    fireEvent.click(screen.getByTestId("draw-card-btn"));
    await waitFor(() => {
      // 立即顯示，不設 defer_strategy
      expect(screen.getByTestId("gacha-result-toast")).toBeInTheDocument();
      expect(screen.getByTestId("gacha-result-toast")).not.toHaveAttribute(
        "data-defer-strategy"
      );
    });
  });

  it("[RISK-09] 連續抽卡 ≥5 次（1 小時內）後顯示冷卻提示", () => {
    render(<GachaDrawButton drawCountInLastHour={5} />);
    expect(screen.getByTestId("gacha-cooldown-hint")).toBeInTheDocument();
    expect(screen.getByTestId("draw-card-btn")).toBeDisabled();
  });

  it("XP 不足時抽卡按鈕禁用並顯示所需費用", () => {
    render(<GachaDrawButton xpBalance={50} drawCost={100} />);
    expect(screen.getByTestId("draw-card-btn")).toBeDisabled();
    expect(screen.getByTestId("xp-insufficient-hint")).toHaveTextContent("需要 100 XP");
  });

  it("抽卡請求送到後端 /api/m6_5/draw_card，前端不自行計算抽取結果", async () => {
    const apiSpy = vi.fn().mockResolvedValue({ item_id: "item_001", rarity: "common" });
    server.use(rest.post("/api/m6_5/draw_card", (req, res, ctx) => {
      apiSpy(req.body);
      return res(ctx.json({ item_id: "item_001", rarity: "common" }));
    }));
    render(<GachaDrawButton xpBalance={500} />);
    fireEvent.click(screen.getByTestId("draw-card-btn"));
    await waitFor(() => expect(apiSpy).toHaveBeenCalled());
  });
});

describe("M3.11.2 程序化任務抽挑戰", () => {
  it("點擊抽挑戰按鈕從 M4.11 取得一個 ZPD 任務", async () => {
    const challengeSpy = vi.fn().mockResolvedValue({ text: "實作 K8s Ingress", difficulty: "stretch" });
    render(<DrawChallengeButton onDraw={challengeSpy} />);
    fireEvent.click(screen.getByTestId("draw-challenge-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("challenge-result-card")).toBeInTheDocument();
      expect(screen.getByTestId("challenge-result-card")).toHaveTextContent("K8s Ingress");
    });
  });

  it("[RISK-07] 抽挑戰介面不含任何質押 XP 的選項", () => {
    render(<DrawChallengeButton />);
    expect(screen.queryByTestId("stake-option")).not.toBeInTheDocument();
  });
});

describe("M3.11.3 隱藏成就無 UI 狀態控制器", () => {
  it("解鎖前，隱藏成就在任何介面不顯示（含灰色格位、問號提示）", () => {
    render(<AchievementGrid collections={[]} dictionary={mockDictionary} />);
    // 隱藏成就（hidden: true）完全不渲染任何佔位符
    const hiddenSlots = screen.queryAllByTestId("hidden-achievement-slot");
    expect(hiddenSlots.length).toBe(0);
  });

  it("已知成就（hidden: false）的鎖定格位仍顯示（有問號佔位）", () => {
    const normalLockedItem = { ...mockItem, hidden: false, unlocked: false };
    render(<AchievementGrid dictionary={[normalLockedItem]} />);
    expect(screen.getByTestId("badge-slot-locked")).toBeInTheDocument();
  });
});

describe("M3.11.4 隱藏成就無預警驚喜彈窗", () => {
  it("收到 HIDDEN_ACHIEVEMENT_UNLOCKED WebSocket 事件後立即彈出驚喜 Modal", async () => {
    const { emitWS } = setupWebSocketMock("/api/m4_12/events");
    render(<HiddenAchievementListener />);
    emitWS({ type: "HIDDEN_ACHIEVEMENT_UNLOCKED", achievement_id: "ha_001", name: "深夜衝刺者" });
    await waitFor(() => {
      expect(screen.getByTestId("surprise-modal")).toBeInTheDocument();
      expect(screen.getByTestId("surprise-modal")).toHaveTextContent("深夜衝刺者");
    });
  });

  it("[RISK-09] 焦慮狀態下系統不主動推播 Gacha 邀請", async () => {
    render(<GachaPromotion implicitState={{ label: "anxiety", confidence: 0.85 }} />);
    expect(screen.queryByTestId("gacha-invite-banner")).not.toBeInTheDocument();
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

```
apps/web/src/components/m3_11_gacha/
  ├── GachaDrawButton/             # M3.11.1 XP 抽卡
  │   ├── index.tsx
  │   ├── GachaResultToast.tsx     # L1 即時顯示（不 defer）
  │   └── useDrawRateLimit.ts      # 連續抽卡冷卻計數
  ├── DrawChallengeButton/         # M3.11.2 抽挑戰
  │   ├── index.tsx
  │   └── ChallengeResultCard.tsx
  ├── HiddenAchievementListener/  # M3.11.3 + M3.11.4
  │   ├── index.tsx                # WebSocket 監聽器（全局掛載）
  │   └── SurpriseModal.tsx        # 無預警驚喜彈窗
  └── GachaPromotion/             # 系統主動推播門禁
      └── index.tsx               # 焦慮狀態下不渲染
```

### 7.2 抽卡結果通道（L1 即時 — RISK-04）

```typescript
// [RISK-04] 抽卡結果屬 L1 即時慶祝，不走 M3.9 defer
async function handleDrawCard() {
  const result = await fetch("/api/m6_5/draw_card", {
    method: "POST",
    body: JSON.stringify({ cost_xp: DRAW_COST }),
  }).then((r) => r.json());

  // 直接 Toast，header 標注 immediate（供 RISK-04 驗收測試使用）
  showToast({
    content: <GachaResultToast item={result} />,
    duration: 3000,
    deferStrategy: "immediate",  // 不走 breakpoint defer
  });
}
```

### 7.3 隱藏成就完全無 UI 狀態（M3.11.3）

```typescript
// [M3.11.3 鐵律] hidden=true 的成就在解鎖前完全不渲染
function AchievementGrid({ dictionary }: { dictionary: Item[] }) {
  // 過濾：hidden=true 且未解鎖 → 完全跳過，不渲染任何佔位符
  const visibleItems = dictionary.filter(
    (item) => !(item.hidden && !item.unlocked_at)
  );
  return (
    <div className="grid grid-cols-6 gap-2">
      {visibleItems.map((item) => (
        <BadgeSlot key={item.id} item={item} />
      ))}
    </div>
  );
}
```

### 7.4 焦慮門禁（RISK-09）

```typescript
// [R09 §3.3 + RISK-09] 系統主動推播門禁
function GachaPromotion({ implicitState }: Props) {
  const isBlocked =
    implicitState?.label === "anxiety" ||
    implicitState?.label === "avoidance" ||
    implicitState?.label === "depression";

  if (isBlocked) return null;  // 完全不渲染推播邀請
  return <GachaInviteBanner />;
}
```

### 7.5 連續抽卡冷卻（RISK-09）

```typescript
// [R09 §3.3] 1 小時內 ≥5 次 → 顯示冷卻提示
export function useDrawRateLimit() {
  const drawHistory = useRef<number[]>([]);
  const WINDOW_MS = 60 * 60 * 1000;  // 1 小時
  const MAX_DRAWS = 5;

  function recordDraw() {
    const now = Date.now();
    drawHistory.current = drawHistory.current.filter((t) => now - t < WINDOW_MS);
    drawHistory.current.push(now);
  }

  const drawCountInLastHour = drawHistory.current.filter(
    (t) => Date.now() - t < WINDOW_MS
  ).length;

  return {
    isCoolingDown: drawCountInLastHour >= MAX_DRAWS,
    drawCountInLastHour,
    recordDraw,
  };
}
```

### 7.6 異常處理

- 抽卡 API 失敗 → 顯示「抽卡失敗，XP 未扣除」Toast，不靜默失敗（避免使用者重複嘗試）
- `HIDDEN_ACHIEVEMENT_UNLOCKED` WebSocket 訊息若在 Modal 已開著時收到 → 排隊等當前 Modal 關閉後再顯示，不疊加
- M4.11 無可用 ZPD 任務（所有任務已完成或難度不匹配）→ 顯示「目前沒有適合你的挑戰，繼續推進專案後再試」

## 8. Anti-patterns

- ❌ **不要讓任何介面暗示隱藏成就的存在**（解鎖前）。包括「還有 3 個隱藏成就未解鎖」的計數、「？」格位、進度條留白——任何暗示都構成 FOMO，違反 M3.11.3 的「絕對無 UI 狀態」原則
- ❌ **不要讓前端自行計算抽卡結果**（偽隨機 Math.random()）。抽卡必須走後端 M6.5 的 ACID 交易，確保「扣 XP → 隨機權重 → 寫入 user_collections」的原子性，防止重複領取（M6.5 SPEC 驗收標準：1000 並發無重複）
- ❌ **不要把隱藏成就驚喜彈窗（M3.11.4）路由到 M3.9 的 defer 通知中心**。驚喜彈窗的心理機制在於「無預警」——若歸檔到通知中心等斷點，使用者會在事後看到，驚喜感消失
- ❌ **不要在系統主動推播 Gacha 邀請時忽略 M4.8 的隱性狀態**。M3.11 是 RISK-09 的直接觸發點；焦慮狀態下的推播等於將賭博式增強注入高壓狀態（R09 §3.3 Replika 案例）

## 9. Open Questions

- [ ] **抽卡費用（`DRAW_COST`）固定還是動態？** 若隨 XP 餘額比例浮動，需要定義費用公式；若固定，固定在多少 XP？
- [ ] **隱藏成就驚喜彈窗的特效等級是否隨稀有度變化？** Legendary 驚喜需要比 Common 更誇張的特效？
- [ ] **「抽挑戰」功能與 M4.11 ZPD 任務池的關係是否唯一？** 抽到的挑戰是否自動加入任務清單，還是使用者需要手動確認接受？
- [ ] **連續抽卡的冷卻時間（目前設 1 小時）是否需要使用者可配置？** 或完全由系統決定不可調整？

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 三種觸發機制均說明，核心原則（驚喜 + 門禁）突出
- [x] §2 至少 3 個 `Rxx §章節` 引用（R01×2, R09）
- [x] §3 Schema 含四個子模組各自的輸入
- [x] §4 依賴是真實模組編號（M4.11、M4.12、M6.5 均為進階）
- [x] §5 RISK-04、RISK-09、RISK-07 均標注且緩解策略具體
- [x] §6 測試覆蓋四個子模組 + L1 即時通道 + 焦慮門禁
- [x] §8 至少 4 條反模式，M3.11.3 鐵律以 ❌ 強調
- [x] §9 至少 4 個開放問題
