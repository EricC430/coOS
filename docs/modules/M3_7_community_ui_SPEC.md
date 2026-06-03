# M3.7 — 社群與社會情懷模組 (Community UI)

**標籤**:`[進階]`
**版本**:`1.0`
**最後更新**:2026-06-03

> **MVP 策略**: Phase 1~5 以 stub 卡片佔位即可。本 SPEC 記錄完整設計,供進階階段實作參考。MVP 閉環完成並產出 `docs/MVP_CLOSURE_REPORT.md` 後才可動工。

## 1. Purpose

以「社交情境隔離」為核心設計原則,提供同儕驗證、公開承諾、XP 質押對賭的社群介面——讓社會情懷的正向外部壓力在「使用者主動選擇的情境」下發揮效果,而非強迫性的社交曝光。

### 1.1 線框圖對應 (軟體介面構想.pdf §4 Community)

PDF 原稿確認以下 Bento Grid 版面結構:

```text
┌──────────────────────────────────────────────────────┬──────────────┐
│                   Community                          │ [Interview   │
│                                                      │  Preparer]   │
│  ┌──────────────────────┬───────────────────────┐   │              │
│  │ Goal / Vision /      │ Weekly/Monthly         │   │ [Total       │
│  │ Codex / Quotes /     │ Community Challenges   │   │  Strangers]  │
│  │ Rules                │                        │   │              │
│  ├──────────────────────┴──────┬────────────────┤   │ [Friend      │
│  │ Posts / Achievements        │ Tasks          │   │  Group]      │
│  │                             │ (to claim)     │   │              │
│  │ 🔵 Boyu 達成了 ... 成就     │                │   │ [Cooking     │
│  │                             │ Commitments    │   │  Lovers]     │
│  │ 🔵 Jacky 分享了鼓勵的話    ├────────────────┤   │              │
│  │    ──────────────────       │ Validation     │   │ [Study       │
│  │                             │                │   │  Group]      │
│  └─────────────────────────────┴────────────────┘   │              │
└──────────────────────────────────────────────────────┴──────────────┘
```

**版面細節** (來自 PDF):

- **整體佈局**: Bento Grid (不規則但對齊的區塊) + 右側垂直子社群導覽列
- **左上 — 社群共識區** (靜態展示):
  - 標籤: `Goal / Vision / Codex / Quotes / Rules`
  - 顯示當前社群的核心精神與行為規範;切換子社群時內容更新
- **右上 — 定期挑戰區**:
  - 標題: `Weekly/Monthly Community Challenges`
  - 大型空白展示近期共同任務;挑戰內容由 M4.11 ZPD 任務池或管理員設定
- **左下 — 成就貼文動態牆** (`Posts / Achievements`):
  - 條列式動態卡片,每則帶使用者頭像圓圈
  - 範例: `Boyu 達成了 ... 成就` (系統自動推播里程碑)
  - 範例: `Jacky 分享了鼓勵的話` (純文字貼文,帶多行橫線)
  - 即時更新 (WebSocket/SSE),新成就立即彈出
- **右下 — 行動承諾區** (切分為兩塊):
  - 左格: `Tasks (to claim)` — 待領取/待解決任務清單
  - 右格: `Commitments` (上) + `Validation` (下),以水平線分隔
  - 三者構成 `Tasks → Commitments → Validation` 行為閉環
- **最右側 — 子社群垂直導覽列**:
  - 垂直線串聯圓形節點按鈕,類似節點地圖設計
  - 預設子社群 (由上到下): `Interview Preparer` / `Total Strangers` / `Friend Group` / `Cooking Lovers` / `Study Group`
  - 點選節點後,左側所有區塊 (Goal/Posts/Challenges/Tasks) 同步切換對應社群資料

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R09 | §4.1 社會情懷 | 同儕驗證作為 SDT「連結」需求的滿足;公開承諾強化外部問責機制 |
| R09 | §3.3 病態使用風險 | 社交壓力切換器 (陌生人/朋友圈) 必須讓使用者可主動降低社交壓力強度 |
| R01 | §α-DPO Dropout 危機 | XP 質押對賭設計必須防範「質押失敗 + 社群羞辱」的複合 Dropout 誘因 |
| R07 | §5 嵌入逆向攻擊 | 社群貼文必須走草稿核准流程,防止 Observer 推論結果透過貼文側通道洩漏 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| `GET /api/m6_6/social_posts` | `SocialPost[]` | `[{ id, user_id, content, likes_count }]` |
| `GET /api/m6_6/communities` | `Community[]` | `[{ id, name, type: "study_group" }]` |
| `GET /api/m6_6/stakes` | `Stake[]` | `[{ id, xp_amount, deadline, status }]` |
| M4.13 承諾驗證事件 (via SSE) | `{ type: "COMMITMENT_VALIDATED", post_id }` | 同儕驗證完成通知 |
| M3.1 `xpBalance` | `number` | 質押餘額確認 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `POST /api/m6_6/social_posts` (草稿送審) | `SocialPostDraft` | `{ content, revealed_metrics, privacy_warning }` |
| `POST /api/m6_6/stakes` | `{ xp_amount, deadline, community_id }` | XP 質押 |
| `POST /api/m6_6/validations` | `{ post_id, validator_id }` | 同儕驗證 |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.7", event: "community_interaction", type }` | 觀測 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M4.13** (損失規避與同儕驗證引擎):質押扣管、社會制約、跨社群權限的後端邏輯
- **M6.6** (社群實體與損失規避擴充):社群貼文、驗證、質押的資料表

### 下游 (誰依賴我)

- **M4.13**:M3.7 的 UI 動作觸發 M4.13 的後端業務邏輯

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-12** | Observer 推論的成就作為貼文上雲,側通道洩漏使用者行為 | M3.7.5 成就貼文必須走使用者手動核准流程;Observer 自動發現的成就預設 `visibility="private"` |
| **RISK-07** | XP 質押 + ZPD 任務失敗 = 複合 Dropout 挫敗 | M3.7.8 質押介面必須顯示「只對成功率 ≥70% 的任務質押」警示;後端 M4.13 強制過濾 |
| **RISK-09** | 高焦慮狀態下社群壓力加劇病態使用 | M3.7.3 社交壓力切換器在 M4.8 偵測焦慮時,自動建議「切換到陌生人模式降低壓力」(不強制) |

## 6. Acceptance Criteria

> **注意**:以下測試僅在進階階段動工前需要通過。MVP 階段測試僅確認 stub 卡片正確佔位。

```typescript
// tests/m3_7/community_ui.test.ts

describe("MVP Stub 驗收", () => {
  it("M3.7 所有子模組渲染 stub 佔位卡片,不報錯", () => {
    render(<CommunityUI stubMode={true} />);
    expect(screen.getByTestId("community-stub")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

describe("M3.7.2 社交隔離子社群切換器 (進階)", () => {
  it("右側垂直 Carousel 切換子社群後正確載入對應貼文", async () => {
    render(<CommunityUI />);
    const communityCarousel = screen.getByTestId("community-carousel");
    fireEvent.click(screen.getAllByTestId("community-item")[1]);
    await waitFor(() => {
      expect(screen.getByTestId("posts-feed")).toHaveAttribute(
        "data-community-id",
        mockCommunities[1].id
      );
    });
  });
});

describe("M3.7.3 社交壓力切換器 (進階)", () => {
  it("切換到陌生人模式後貼文作者顯示匿名化", () => {
    render(<SocialPressureToggle mode="stranger" posts={mockPosts} />);
    screen.getAllByTestId("post-author").forEach((author) => {
      expect(author).toHaveTextContent("匿名");
    });
  });
});

describe("M3.7.5 成就貼文 (進階 — RISK-12)", () => {
  it("Observer 自動發現的成就預設 visibility=private,不出現在貼文動態牆", () => {
    render(<PostsFeed posts={[mockPrivateAchievement]} />);
    expect(screen.queryByTestId("achievement-post")).not.toBeInTheDocument();
  });

  it("手動發布成就時顯示隱私警告說明公開內容", async () => {
    render(<AchievementPublishModal achievement={mockAchievement} />);
    fireEvent.click(screen.getByTestId("publish-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("privacy-warning")).toBeInTheDocument();
      expect(screen.getByTestId("privacy-warning")).toHaveTextContent(
        "此貼文將公開以下資訊"
      );
    });
  });
});

describe("M3.7.8 XP 質押介面 (進階 — RISK-07)", () => {
  it("質押按鈕在任務成功率 < 70% 時顯示警示並禁用", () => {
    render(<StakeButton task={mockLowSuccessTask} userEstimatedSuccess={0.5} />);
    expect(screen.getByTestId("stake-btn")).toBeDisabled();
    expect(screen.getByTestId("stake-warning")).toBeInTheDocument();
  });
});
```

## 7. Implementation Notes

### 7.1 MVP Stub 實作

```typescript
// apps/web/src/components/m3_7_community/index.tsx
// MVP 階段只需此 stub 元件
export function CommunityUI({ stubMode = true }: { stubMode?: boolean }) {
  if (stubMode) {
    return (
      <div data-testid="community-stub" className="community-stub-card">
        <p>社群功能將在進階階段開放</p>
      </div>
    );
  }
  // 完整實作在進階階段
  return <FullCommunityUI />;
}
```

### 7.2 子模組結構 (進階階段)

```text
apps/web/src/components/m3_7_community/
  ├── index.tsx                        # stub / 完整版切換
  ├── BentoGridLayout.tsx              # M3.7.1
  ├── CommunityCarousel.tsx            # M3.7.2 垂直 Carousel
  ├── SocialPressureToggle.tsx         # M3.7.3
  ├── CommunityCodexPanel.tsx          # M3.7.4 Goal / Vision / Codex
  ├── PostsFeed.tsx                    # M3.7.5
  ├── ChallengeBoardPanel.tsx          # M3.7.6 週期挑戰
  ├── CommitmentClosedLoop.tsx         # M3.7.7
  └── StakeXPInterface.tsx             # M3.7.8
```

### 7.3 社群貼文草稿核准流程 (M3.7.5 — RISK-12)

```typescript
// [R07 §5 + R08 §草稿與核准] 貼文必須先產生草稿讓使用者確認
async function proposePost(achievement: Achievement): Promise<SocialPostDraft> {
  return {
    content: achievement.public_description,
    revealed_metrics: achievement.metrics_to_show,
    privacy_warning: `此貼文將公開以下資訊:\n${achievement.metrics_to_show.join("\n")}`,
    requires_explicit_publish: true, // 等使用者按 publish
  };
}
```

### 7.4 質押門禁 (M3.7.8 — RISK-07)

```typescript
// [R01 §REJECT + RISK-07] 前端質押門禁
function canStake(userEstimatedSuccess: number, zpd_zone: string): boolean {
  if (userEstimatedSuccess < 0.70) return false;
  if (zpd_zone === "edge") return false;
  return true;
}
```

### 7.5 異常處理

- 社群 API 離線 → 顯示「社群暫時無法使用」,不影響其他 M3.x 模組
- 質押交易失敗 → 顯示失敗原因,不靜默重試
- 同儕驗證 WebSocket 斷線 → 以輪詢方式補齊未收到的驗證事件

## 8. Anti-patterns

- ❌ **不要在 MVP 階段實作 M3.7 的任何完整功能**。使用 stub 佔位,防止建立對 M4.13、M6.6 等進階依賴的硬連結,確保 MVP 在進階模組全數移除時仍可獨立運作
- ❌ **不要允許 Observer 自動推論的成就直接發布為社群貼文**。必須走草稿核准流程;預設 `visibility="private"` (RISK-12)
- ❌ **不要在使用者焦慮狀態下推播質押邀請**。前端 M3.7.8 需讀取 M4.8 狀態;後端 M4.13 同樣有門禁 (RISK-07、RISK-09)
- ❌ **不要讓跨社群的資料混用**。讀書會社群的貼文不可出現在陌生人社群動態牆,由 M4.13.3 的跨社群權限隔離中介軟體保障

## 9. Open Questions

- [ ] **社群的建立由誰發起?** 使用者自建,還是系統預設幾個社群 (讀書會/陌生人/朋友圈) 後讓使用者加入?
- [ ] **XP 質押的對賭對象是誰?** 與系統對賭 (質押金放入獎池等 XP 到期) 還是需要另一個真實使用者?
- [ ] **週期挑戰 (M3.7.6) 的挑戰內容由誰生成?** M4.11 ZPD 任務池,還是社群管理員手動設定?
- [ ] **同儕驗證的判定標準是什麼?** 純社交點贊,還是需要提交「驗證截圖」?

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 說明核心原則:社交情境隔離
- [x] §2 至少 4 個 `Rxx §章節` 引用
- [x] §3 Schema 完整
- [x] §4 依賴是真實模組編號
- [x] §5 RISK-07、RISK-09、RISK-12 均標注
- [x] §6 測試含 MVP Stub 驗收 + 進階功能測試
- [x] §8 至少 4 條反模式含 MVP 守門邏輯
- [x] §9 至少 4 個開放問題
