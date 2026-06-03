# M3.9 — 防疲勞非同步通知儀表板 (Async Notification Dashboard)

**標籤**:`[進階]`
**版本**:`1.0`
**最後更新**:2026-06-03

> **MVP 策略**：Phase 1~5 不動工。MVP 期間 L2 通知由 M3.4 側邊欄的 Badge 計數暫代，不需獨立儀表板頁面。需等 MVP 閉環後才可實作本模組。

## 1. Purpose

將所有「不緊急的系統主動洞察」（反思草稿、Observer 行為觀察、Persona 建議）靜默歸檔至通知中心，僅在 M1.2 斷點信號到達時溫和浮現——從根本上消滅「通知疲勞」，讓通知從打斷源轉變為斷點期間的主動查閱工具。

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §三 醫療級警報疲勞防範 | M3.9.1 靜默歸檔：不在高認知負荷時推送，仿效 ICU 警報分級管理 |
| R08 | §二 任務斷點打斷管理 | M3.9.2 延遲恢復提示：只在 M1.2 偵測到自然斷點後才溫和浮現 |
| R08 | §四.2 微摩擦力的必要性 | M3.9.3 批次審閱：鼓勵使用者主動批閱而非被動接收，維持作者身分 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.4 反思草稿就緒事件（L2 通知） | `{ type: "DRAFT_READY", reflection_id, date }` | `{ type: "DRAFT_READY", reflection_id: "r_001" }` |
| M4.6 Observer 洞察事件（L2 通知） | `{ type: "OBSERVER_INSIGHT", content, confidence }` | `{ type: "OBSERVER_INSIGHT", content: "你這週 coding 時間比上週多 40%" }` |
| M4.2 Persona 建議（L2 通知） | `{ type: "PERSONA_NUDGE", persona_id, message }` | `{ type: "PERSONA_NUDGE", message: "記得休息一下" }` |
| M1.2 `BREAKPOINT_DETECTED` 事件 | `{ confidence: number, breakpoint_type: string }` | `{ confidence: 0.85, breakpoint_type: "cursor_pause" }` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| 前端通知中心 UI（`/notifications` 路由或側邊板） | 通知列表 | — |
| M3.3 草稿彈窗觸發 | `{ reflection_id }` | 使用者從通知點入草稿 |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.9", event: "notification_reviewed", type, latency_seconds }` | `latency_seconds`：從產生到使用者查閱的延遲 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M1.2** (斷點偵測引擎)：通知浮現的門禁信號；無 `BREAKPOINT_DETECTED` 則通知保持靜默
- **M4.4** (草稿生成器)：反思草稿就緒通知的產生源
- **M4.6** (Observer Agent)：行為洞察通知的產生源
- **M4.2** (Persona 狀態機)：Persona 主動 nudge 的產生源

### 下游 (誰依賴我)

- **M3.3** (日報反思模組)：使用者從通知中心點入草稿，跳轉到 M3.3 彈窗

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-04** | L2 通知若不經斷點直接顯示，破壞深度工作並觸發警報疲勞 | M3.9 的所有顯示邏輯必須以 `BREAKPOINT_DETECTED` 事件為門禁；Cron 或 SSE 觸發時只做入庫，不更新 UI |
| （自定義） | 通知積壓超過 20 條時，使用者面對「通知山」產生迴避心態 | M3.9.1 超過 10 條未讀時顯示「今日批次審閱」入口，將多條通知合併為一次批閱動作，降低決策疲勞 |

## 6. Acceptance Criteria

```typescript
// tests/m3_9/notification_dashboard.test.ts

describe("M3.9.1 靜默歸檔通知中心", () => {
  it("[RISK-04] 收到 L2 通知時不立即顯示，僅入庫計數", () => {
    const { store } = renderWithStore(<NotificationDashboard />);
    store.dispatch(receiveL2Notification({ type: "DRAFT_READY", reflection_id: "r_001" }));
    // Badge 計數更新，但通知面板不打開
    expect(screen.getByTestId("notification-badge")).toHaveTextContent("1");
    expect(screen.queryByTestId("notification-panel")).not.toBeInTheDocument();
  });

  it("通知按類型正確分類（草稿 / 洞察 / Nudge）", () => {
    render(<NotificationList items={mockNotifications} />);
    expect(screen.getByTestId("tab-draft")).toBeInTheDocument();
    expect(screen.getByTestId("tab-insight")).toBeInTheDocument();
    expect(screen.getByTestId("tab-nudge")).toBeInTheDocument();
  });
});

describe("M3.9.2 延遲恢復低干擾提示", () => {
  it("[RISK-04] 收到 BREAKPOINT_DETECTED 後通知面板溫和浮現", async () => {
    const { store } = renderWithStore(<NotificationDashboard />);
    store.dispatch(receiveL2Notification({ type: "DRAFT_READY", reflection_id: "r_001" }));
    // 斷點到達
    store.dispatch(breakpointDetected({ confidence: 0.85 }));
    await waitFor(() => {
      // 面板顯示，但不是強制 Modal（不阻擋操作）
      expect(screen.getByTestId("notification-gentle-prompt")).toBeInTheDocument();
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("浮現動畫是溫和滑入而非彈跳警示", () => {
    render(<NotificationGentlePrompt visible={true} />);
    const el = screen.getByTestId("notification-gentle-prompt");
    // 動畫類名驗證（不含 bounce 或 shake）
    expect(el.className).not.toMatch(/bounce|shake|pulse/);
    expect(el.className).toMatch(/slide|fade/);
  });
});

describe("M3.9.3 每日批次審閱", () => {
  it("超過 10 條未讀通知時顯示批次審閱入口", () => {
    const manyNotifications = Array.from({ length: 11 }, (_, i) => ({
      id: `n_${i}`, type: "OBSERVER_INSIGHT",
    }));
    render(<NotificationDashboard notifications={manyNotifications} />);
    expect(screen.getByTestId("batch-review-entry")).toBeInTheDocument();
  });

  it("批次審閱模式一次展示當日所有通知，用戶可一鍵全部標記已讀", async () => {
    render(<BatchReviewModal notifications={mockNotifications} />);
    fireEvent.click(screen.getByTestId("mark-all-read-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("all-read-confirmation")).toBeInTheDocument();
    });
  });

  it("草稿通知點入後跳轉到 M3.3 草稿彈窗", () => {
    const navigate = vi.fn();
    render(
      <NotificationItem
        item={{ type: "DRAFT_READY", reflection_id: "r_001" }}
        onNavigate={navigate}
      />
    );
    fireEvent.click(screen.getByTestId("notification-item"));
    expect(navigate).toHaveBeenCalledWith("/draft/r_001");
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

```
apps/web/src/components/m3_9_notifications/
  ├── index.tsx                        # 通知儀表板頁面 / 側邊板
  ├── NotificationList.tsx             # M3.9.1 靜默歸檔列表
  ├── NotificationGentlePrompt.tsx     # M3.9.2 斷點到達後的溫和提示
  └── BatchReviewModal.tsx             # M3.9.3 批次審閱視窗
```

### 7.2 通知三層分類（對應 RISK-04 緩解策略）

根據 `05_integration_risk_audit.md` RISK-04 定義的三層通知分類：

| 類別 | 觸發來源 | 路由 | 是否經 M3.9 |
| ---- | -------- | ---- | ----------- |
| **L1 即時慶祝** | Gacha 結果、徽章解鎖（使用者主動觸發） | Toast（1.5s）直接顯示 | ❌ 不經 M3.9 |
| **L2 系統洞察** | 草稿就緒、Observer 洞察、Persona Nudge | M3.9 靜默歸檔 → 斷點浮現 | ✅ |
| **L3 安全警示** | CARE 安全資源、隱私洩漏警告 | 強制 Modal（不可繞過） | ❌ 不經 M3.9 |

### 7.3 Zustand 通知狀態切片

```typescript
// 通知狀態只在 Zustand 中維護，不需要後端持久化（進階階段可選）
interface NotificationState {
  pending: Notification[];          // 已入庫但未顯示
  shown: Notification[];            // 已顯示
  isGentlePromptVisible: boolean;   // 斷點到達後顯示

  addNotification: (n: Notification) => void;
  showGentlePrompt: () => void;     // 由 M1.2 斷點事件觸發
  markRead: (id: string) => void;
  markAllRead: () => void;
}
```

### 7.4 斷點門禁整合

```typescript
// [R08 §三 + RISK-04] 訂閱 M1.2 斷點事件，才允許通知浮現
useEffect(() => {
  const unsubBreakpoint = useCoOSStore.subscribe(
    (state) => state.lastBreakpointAt,
    (breakpointAt) => {
      if (breakpointAt && useNotificationStore.getState().pending.length > 0) {
        useNotificationStore.getState().showGentlePrompt();
      }
    }
  );
  return unsubBreakpoint;
}, []);
```

### 7.5 異常處理

- SSE 連線斷線導致通知遺失 → 重連後拉取 `GET /api/m3_9/pending_notifications` 補齊
- 通知積壓 > 50 條（異常情況）→ 強制觸發批次審閱，防止記憶體無限增長
- 使用者關閉通知面板 → `isGentlePromptVisible = false`，等下一次斷點才再次嘗試

## 8. Anti-patterns

- ❌ **不要讓 M3.9 的任何通知在 `BREAKPOINT_DETECTED` 信號到來前主動顯示**。包括 Badge 動畫閃爍也算一種「打斷」——Badge 數字更新靜默，不加動畫（RISK-04）
- ❌ **不要讓草稿通知使用 Modal 形式彈出**。草稿 Modal（M3.3.3）是使用者點入後才觸發的動作；M3.9 只提供入口，不強制開啟
- ❌ **不要把 L1 即時慶祝（Gacha、徽章）路由到 M3.9**。L1 必須即時顯示，繞過 M3.9 的 Defer 機制（見 RISK-04 三層分類表）
- ❌ **不要讓通知在 App 重啟後遺失**。進階階段需要後端持久化；MVP Stub 期間至少保持在記憶體中直到使用者明確關閉

## 9. Open Questions

- [ ] **通知是否需要後端持久化？** 目前設計為純前端記憶體狀態；若 App 崩潰，未讀通知全部遺失。進階階段是否需要 `m6_x_notifications` 表？
- [ ] **`BREAKPOINT_DETECTED` 信號到達後，通知面板顯示多久自動收回？** 需要 timeout 設計（例：使用者 30 秒未互動則收回）
- [ ] **M3.9 是一個獨立頁面（`/notifications`）還是側邊抽屜（Drawer）？** 影響 M3.2 儀表板的佈局空間分配
- [ ] **通知的優先序如何決定？** 當同一個斷點有 3 種不同類型的通知待顯示，哪個優先？

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 單一職責：將打斷轉化為斷點查閱
- [x] §2 至少 3 個 `Rxx §章節` 引用（R08×3）
- [x] §3 Schema 含三層通知類型定義
- [x] §4 依賴是真實模組編號（含 M1.2 門禁依賴）
- [x] §5 RISK-04 標注 + 自定義積壓風險
- [x] §6 測試覆蓋靜默入庫、斷點浮現、批次審閱三個子模組
- [x] §8 至少 4 條反模式含三層分類原則
- [x] §9 至少 4 個開放問題
