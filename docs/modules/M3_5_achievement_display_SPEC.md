# M3.5 — 視覺化成就展示模組 (Achievement Display)

**標籤**:`[MVP]`
**版本**:`1.0`
**最後更新**:2026-06-03

## 1. Purpose

以 Master-Detail 佈局靜態展示使用者已解鎖的徽章與成就,提供「我擁有什麼」的視覺回饋——讓累積的 XP 消費有實體對應物,強化遊戲化的擁有感。本模組只負責展示;抽卡互動 (Gacha) 屬進階 M3.11。

### 1.1 線框圖對應 (軟體介面構想.pdf §1 Collection)

PDF 原稿確認以下版面結構:

```text
┌───────────────────────────────────────────────────────────────┐
│  Collection                          XP 1234  [抽背景] [抽物件]│
│                                                        [微章]  │
│  ┌──────────────────────────────┐   ┌──────────────────────┐  │
│  │  (空白槽位)                  │   │  🎓  XX             │  │
│  ├──────────────────────────────┤   │  ─────────────────   │  │
│  │  🎓  (學士帽圖示)             │   │  (詳細描述多行)      │  │
│  ├──────────────────────────────┤   └──────────────────────┘  │
│  │  CPE  🚩                     │                              │
│  └──────────────────────────────┘                              │
│  收集 XP 可能可以抽取紀念徽章                                    │
└───────────────────────────────────────────────────────────────┘
```

**版面細節** (來自 PDF):

- **頁面標題**: 左上角 `Collection`;右上角顯示 `XP 1234` (當前 XP 餘額,加粗顯示)
- **右上角 Gacha 入口** (進階 M3.11 實作,本模組 MVP 階段以佔位渲染):
  - `[抽背景]` — 消耗 XP 抽取角色空間背景
  - `[抽物件 / 徽章]` — 消耗 XP 抽取裝飾品或成就徽章
  - 兩個按鈕使用盲盒樣式,hover 時顯示當前 XP 是否足夠
- **左側收藏展示區** (垂直排列的長方形槽位):
  - 第一格: 空白,預留未來新收藏
  - 第二格: 學士帽圖示 (代表 UNI/大學階段里程碑)
  - 第三格: `CPE` 字樣 + 旗幟圖示 (大學程式能力檢定轉化為虛擬資產)
  - 鎖定格位: 只顯示問號輪廓,不透露解鎖條件
- **右側詳細資訊面板** (點擊左側槽位後連動):
  - 選取物件的圖示 (如學士帽)
  - 標題 (`XX` 佔位符,實際為徽章名稱)
  - 多行橫線代表詳細描述 (取得日期、背後故事、解鎖條件)
- **底部說明文字**: `收集 XP 可能可以抽取紀念徽章` — 點出 XP 經濟循環

> ⚠️ **MVP 階段**:右上角 `[抽背景]` / `[抽物件]` 按鈕渲染為 disabled 狀態並加上 tooltip `"解鎖進階功能後開放"`,XP 顯示正常運作。Gacha 互動邏輯在 M3.11 實作。

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R09 | §第三章 HAIA 三階段 | 可見的成就收藏品強化 HAIA 第二階段「依附」:使用者對自己的 coOS 檔案產生情感連結 |
| R01 | §α-DPO Dropout 危機 | 成就展示作為成就的「退縮緩衝」:在低動力期看到過去成就可防止 Dropout |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| `GET /api/m6_5/user_collections` | `UserCollection[]` | `[{ item_id, name, rarity, image_url, acquired_at }]` |
| `GET /api/m6_5/items_dictionary` | `Item[]` | 全部可解鎖物品字典 (含未解鎖,用於顯示鎖定狀態) |
| M3.1 `xpBalance` | `number` | 計算當前可消費餘額 (顯示用) |
| M4.12 WebSocket `ACHIEVEMENT_UNLOCKED` 事件 (進階,當 M3.11 實作後) | `{ item_id: string }` | 即時解鎖通知 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| 無後端寫入 (純展示模組) | — | — |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.5", event: "achievement_viewed", item_id }` | 使用者點開徽章詳情 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M3.1** (全域狀態):提供 `xpBalance` 顯示用
- **M6.5** (遊戲化交易引擎):`user_collections` 與 `items_dictionary` 的資料來源

### 下游 (誰依賴我)

- **M3.11** (Gacha 抽卡,進階):使用 M3.5 的 CSS Grid 徽章槽位佈局作為基礎,在解鎖時觸發動畫

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-09 | 若成就展示頁面觸發 Gacha 推廣入口,在焦慮狀態下可能誘發病態使用 | M3.5 本身**不含任何 Gacha 入口**;Gacha 入口僅在 M3.11 中,且受 M4.8 狀態門禁 |

## 6. Acceptance Criteria

```typescript
// tests/m3_5/achievement_display.test.ts

describe("M3.5.1 Master-Detail 佈局", () => {
  it("左側 CSS Grid 顯示所有已解鎖徽章槽位", () => {
    render(<AchievementGrid collections={mockCollections} />);
    const slots = screen.getAllByTestId("badge-slot");
    expect(slots.length).toBe(mockCollections.length);
  });

  it("點擊徽章後右側顯示解鎖條件與描述", async () => {
    render(<AchievementMasterDetail collections={mockCollections} />);
    fireEvent.click(screen.getAllByTestId("badge-slot")[0]);
    await waitFor(() => {
      expect(screen.getByTestId("badge-detail-panel")).toBeInTheDocument();
      expect(screen.getByTestId("badge-unlock-condition")).not.toBeEmptyDOMElement();
    });
  });

  it("未解鎖徽章顯示灰色鎖定狀態,不顯示詳細條件", () => {
    render(<AchievementGrid collections={[]} dictionary={mockDictionary} />);
    const lockedSlots = screen.getAllByTestId("badge-slot-locked");
    lockedSlots.forEach((slot) => {
      expect(slot).toHaveClass("locked");
    });
    fireEvent.click(lockedSlots[0]);
    expect(screen.queryByTestId("badge-detail-panel")).not.toBeInTheDocument();
  });
});

describe("M3.5.2 已解鎖背景與徽章網格展示庫", () => {
  it("稀有度不同的徽章顯示不同的框架樣式", () => {
    render(<BadgeSlot item={{ rarity: "legendary", image_url: "..." }} />);
    expect(screen.getByTestId("badge-frame")).toHaveClass("rarity-legendary");
  });

  it("徽章圖片載入失敗時顯示 fallback 佔位符", () => {
    render(<BadgeSlot item={{ rarity: "common", image_url: "invalid-url" }} />);
    const img = screen.getByRole("img");
    fireEvent.error(img);
    expect(screen.getByTestId("badge-image-fallback")).toBeInTheDocument();
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

```text
apps/web/src/components/m3_5_achievements/
  ├── AchievementMasterDetail/     # M3.5.1
  │   ├── index.tsx
  │   ├── AchievementGrid.tsx      # 左側 CSS Grid
  │   └── BadgeDetailPanel.tsx     # 右側詳情
  └── BadgeSlot/                   # M3.5.2
      ├── index.tsx
      └── rarityStyles.ts          # 稀有度樣式定義
```

### 7.2 CSS Grid 徽章槽位

```typescript
// apps/web/src/components/m3_5_achievements/AchievementGrid.tsx
// [R09 §HAIA] 視覺佈局強化收藏品的「擁有感」
function AchievementGrid({ collections, dictionary }: Props) {
  const unlockedIds = new Set(collections.map((c) => c.item_id));
  return (
    <div className="grid grid-cols-6 gap-2">
      {dictionary.map((item) =>
        unlockedIds.has(item.id) ? (
          <BadgeSlot key={item.id} item={item} unlocked />
        ) : (
          <BadgeSlot key={item.id} item={item} unlocked={false} />
        )
      )}
    </div>
  );
}
```

### 7.3 稀有度樣式對應

| 稀有度 | CSS class | 視覺特徵 |
| ------ | --------- | -------- |
| `common` | `rarity-common` | 灰色細框 |
| `rare` | `rarity-rare` | 藍色發光框 |
| `epic` | `rarity-epic` | 紫色脈衝框 |
| `legendary` | `rarity-legendary` | 金色閃爍框 + 粒子特效 |

### 7.4 異常處理

- `items_dictionary` API 失敗 → 僅顯示已解鎖的收藏品,不顯示鎖定格位
- 徽章圖片 URL 失效 → 顯示模組編號與稀有度的文字佔位符
- 空收藏 (新使用者) → 顯示引導文案「完成第一個反思草稿即可解鎖你的首個徽章」

## 8. Anti-patterns

- ❌ **不要在 M3.5 中放入任何 Gacha 入口按鈕**。Gacha 是進階功能 (M3.11),且受 M4.8 焦慮門禁保護 (RISK-09);M3.5 只負責展示已有成就
- ❌ **不要讓未解鎖徽章顯示解鎖條件的詳細說明**。隱藏成就的驚喜感 (M3.11 的核心設計) 從 M3.5 就必須維持:鎖定格位只顯示問號輪廓,不透露條件
- ❌ **不要直接從 `raw_tracking_logs` 計算成就**。成就計算屬 M4.12 的職責;M3.5 只讀取 M6.5 已確認的 `user_collections`

## 9. Open Questions

- [ ] **成就展示是否按角色分類?** 例如「資工系大學生」角色解鎖的徽章只在該角色頁面顯示,還是統一在成就庫?
- [ ] **`acquired_at` 時間戳是否在徽章詳情中顯示?** 對使用者是否有意義?

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 單一職責:純展示,不含 Gacha
- [x] §2 至少 2 個 `Rxx §章節` 引用
- [x] §3 Schema 完整
- [x] §4 依賴是真實模組編號
- [x] §5 grep 過 `05_integration_risk_audit.md` (RISK-09 標注)
- [x] §6 測試涵蓋兩個子模組
- [x] §8 至少 3 條反模式
- [x] §9 至少 1 個開放問題
