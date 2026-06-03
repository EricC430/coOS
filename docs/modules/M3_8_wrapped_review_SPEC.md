# M3.8 — 週期性回顧 Wrapped 彈窗 (Periodic Wrapped Review)

**標籤**:`[進階]`
**版本**:`1.0`
**最後更新**:2026-06-03

> **MVP 策略**：Phase 1~5 不動工。需等 MVP 閉環完成並產出 `docs/MVP_CLOSURE_REPORT.md` 後才可實作。`daily_reflections.mood_score` 欄位需先在 M6.4 定義。

## 1. Purpose

每週或每月自動結算使用者的成長數據，以**敘事性故事卡片**（而非純數字報表）呈現成長軌跡——讓量化指標轉化為有情感意義的敘事，強化使用者對自身進步的主觀感知。

> ⚠️ **RISK-10 核心危險點**：低落週若以慶祝語氣呈現「動力提升 20%」，使用者感受到系統不理解自己 → 信任崩潰。必須先讀絕對水平再決定敘事框架。

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R10 | §敘事化福祉 Narrating Fitness | M3.8.1 週期結算以故事性而非統計性語言呈現：「你撐過了這週」比「完成率 60%」更有情感效果 |
| R10 | §典範轉移 量化自我→質性自我 | Wrapped 的敘事卡片是「量化行為數據 → 質性個人敘事」的具體實現 |
| R05 | §諂媚效應 | M3.8.2 渲染邏輯必須避免虛假樂觀；低落週的敘事絕不能用慶祝詞彙（對應 RISK-10） |
| R01 | §α-DPO Dropout 危機 | Wrapped 在連續低動力週後應以「退縮緩衝」框架呈現，而非繼續施壓 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| `GET /api/m6_4/weekly_summary` | `WeeklyMetrics { week_start, tasks_done, mood_score_avg, motivation_delta, top_role }` | `{ mood_score_avg: 2.5, motivation_delta: 0.20, tasks_done: 4 }` |
| `GET /api/m6_4/monthly_summary` | `MonthlyMetrics { month, xp_earned, reflections_completed, streaks }` | 月度版同上 |
| M3.1 週期性 Cron 事件（週一 09:00 / 月初）| `{ type: "WEEKLY_WRAPPED_DUE" \| "MONTHLY_WRAPPED_DUE" }` | 觸發彈窗 |
| M1.2 `BREAKPOINT_DETECTED` | `{ confidence: number }` | 在斷點時才推送彈窗，不在深度工作中彈出 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| 前端 Wrapped Modal（僅顯示，無 DB 寫入） | React Modal + Framer Motion | — |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.8", event: "wrapped_viewed", period, mood_tier }` | `{ period: "weekly", mood_tier: "low" }` |

## 4. Dependencies

### 上游 (我依賴誰)

- **M6.4** (日報反思核心實體)：提供週 / 月度聚合統計，含 `mood_score_avg`
- **M1.2** (斷點偵測引擎)：Wrapped 彈窗屬 L2 系統洞察，必須等 `BREAKPOINT_DETECTED` 才推送（不在高認知負荷時彈出）
- **M4.5** (XP 結算)：月度 Wrapped 需要 `xp_earned` 資料

### 下游 (誰依賴我)

- 無其他模組依賴 M3.8（純展示層，終端節點）

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-10** | 低落週（mood_score_avg < 4）以慶祝語氣呈現相對提升 → 信任崩潰、Gaslighting 感 | `generate_wrapped_narrative()` 必須先讀 `mood_score_avg` 的**絕對水平**：低落週用陪伴口吻，不用慶祝詞彙；高昂週才可慶祝 |
| **RISK-04** | Wrapped 彈窗不經斷點直接彈出，破壞深度工作 | 彈窗屬 L2 Defer：僅在 M1.2 `BREAKPOINT_DETECTED` 信號後才浮現；Cron 觸發只設 pending 旗標，不立即彈 |
| （自定義） | 連續多週低落 → 每週 Wrapped 反覆呈現「你又撐過了」→ 累積消沉感 | 連續 ≥3 週 `mood_score_avg < 4` → 切換到「關懷模式」：隱藏統計數字，只顯示一句話 + 建議聯繫支持資源 |

## 6. Acceptance Criteria

```typescript
// tests/m3_8/wrapped_review.test.ts

describe("M3.8.1 週期結算邏輯", () => {
  it("[RISK-10] mood_score_avg < 4 時敘事不含慶祝詞彙", () => {
    const narrative = generateWrappedNarrative({
      moodScoreAvg: 2.5,
      motivationDelta: 0.20,
      tasksDone: 4,
    });
    const forbiddenWords = ["恭喜", "提升", "突破", "滿格", "棒", "厲害"];
    forbiddenWords.forEach((word) => {
      expect(narrative).not.toContain(word);
    });
  });

  it("[RISK-10] mood_score_avg >= 7 時可使用積極詞彙", () => {
    const narrative = generateWrappedNarrative({
      moodScoreAvg: 8.0,
      motivationDelta: 0.30,
      tasksDone: 12,
    });
    // 高昂週應包含正向敘事
    expect(narrative.length).toBeGreaterThan(20);
    // 不應顯示「撐過了」等低落框架
    expect(narrative).not.toContain("撐過");
  });

  it("中性週（4 ≤ mood < 7）以平實語氣呈現", () => {
    const narrative = generateWrappedNarrative({
      moodScoreAvg: 5.0,
      motivationDelta: 0.05,
      tasksDone: 7,
    });
    expect(narrative).toContain("完成");
    // 既不慶祝也不是陪伴口吻
    expect(narrative).not.toContain("撐過");
    expect(narrative).not.toContain("恭喜");
  });

  it("連續 3 週低落切換到關懷模式，隱藏統計數字", () => {
    const narrative = generateWrappedNarrative({
      moodScoreAvg: 2.0,
      consecutiveLowWeeks: 3,
    });
    // 關懷模式不顯示百分比或數字
    expect(narrative).not.toMatch(/\d+%/);
    expect(narrative).toContain("支持");  // 顯示支持資源提示
  });
});

describe("M3.8.2 Wrapped 彈窗與視覺特效", () => {
  it("[RISK-04] Cron 觸發後彈窗不立即顯示，等待 BREAKPOINT_DETECTED", async () => {
    const { store } = renderWithStore(<WrappedModal />);
    // 模擬 Cron 觸發
    store.dispatch(setWrappedPending("weekly"));
    // 此時不應顯示彈窗
    expect(screen.queryByTestId("wrapped-modal")).not.toBeInTheDocument();
    // 收到斷點信號後才顯示
    store.dispatch(breakpointDetected());
    await waitFor(() => {
      expect(screen.getByTestId("wrapped-modal")).toBeInTheDocument();
    });
  });

  it("低落週 Wrapped 不播放多巴胺特效動畫", () => {
    render(<WrappedModal metrics={{ moodScoreAvg: 2.5 }} visible={true} />);
    expect(screen.queryByTestId("dopamine-animation")).not.toBeInTheDocument();
  });

  it("高昂週 Wrapped 播放慶祝動畫", () => {
    render(<WrappedModal metrics={{ moodScoreAvg: 8.0 }} visible={true} />);
    expect(screen.getByTestId("dopamine-animation")).toBeInTheDocument();
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

```
apps/web/src/components/m3_8_wrapped/
  ├── index.tsx                    # Wrapped Modal 容器
  ├── WrappedNarrative.tsx         # M3.8.1 敘事卡片
  ├── WrappedAnimation.tsx         # M3.8.2 多巴胺視覺特效（高昂週限定）
  └── useWrappedTrigger.ts         # Cron → pending → BREAKPOINT → 顯示
```

### 7.2 敘事框架決策樹（M3.8.1）

```typescript
// [R10 §敘事化福祉 + R05 §諂媚效應 + RISK-10]
export function generateWrappedNarrative(metrics: WeeklyMetrics): string {
  // 連續低落優先判斷（覆蓋其他分支）
  if ((metrics.consecutiveLowWeeks ?? 0) >= 3) {
    return `這陣子你承受了不少。不需要強迫自己有成果——你還在，就已經很好了。需要的話，可以找人聊聊。`;
  }

  if (metrics.moodScoreAvg < 4) {
    // [RISK-10] 低落週：陪伴口吻，不呈現相對提升
    return `這週你撐過來了。雖然心情有些低落，但你還是完成了 ${metrics.tasksDone} 項任務。`;
  }

  if (metrics.moodScoreAvg >= 7) {
    // 高昂週：可慶祝，呈現相對指標
    const deltaStr = metrics.motivationDelta > 0
      ? `動力比上週提升了 ${Math.round(metrics.motivationDelta * 100)}%`
      : `保持了穩定的節奏`;
    return `動力滿格的一週！${deltaStr}，完成 ${metrics.tasksDone} 項任務。繼續保持。`;
  }

  // 中性週
  return `這週你完成了 ${metrics.tasksDone} 項任務，動力穩定。`;
}
```

### 7.3 Defer 觸發機制（M3.8 — RISK-04）

```typescript
// [RISK-04] Wrapped 屬 L2 defer：Cron 設旗標，斷點才顯示
export function useWrappedTrigger() {
  const [pending, setPending] = useState<"weekly" | "monthly" | null>(null);
  const breakpointDetected = useCoOSStore((s) => s.lastBreakpointAt);

  // Cron 觸發：只設 pending，不彈窗
  useEffect(() => {
    const handler = (e: CustomEvent) => setPending(e.detail.period);
    window.addEventListener("WRAPPED_DUE", handler as EventListener);
    return () => window.removeEventListener("WRAPPED_DUE", handler as EventListener);
  }, []);

  // 斷點到達 + 有 pending → 才顯示
  const shouldShow = pending !== null && breakpointDetected !== null;
  return { shouldShow, period: pending, clearPending: () => setPending(null) };
}
```

### 7.4 異常處理

- `weekly_summary` API 失敗 → 不強制顯示 Wrapped，將 pending 旗標延到下次斷點重試
- `mood_score_avg` 資料缺失（新使用者 / 反思未完成）→ 以任務完成數為主要指標，不顯示 mood 相關敘事
- 使用者關閉 Wrapped 彈窗後，`pending` 旗標清除，不在同週期內再次顯示

## 8. Anti-patterns

- ❌ **不要把相對指標（「提升 20%」）從絕對水平脫離單獨呈現**。2/10 提升 20% 仍是 2.4/10，若呈現為成就，觸發 Gaslighting 感（RISK-10）
- ❌ **不要讓 Wrapped 在 Cron 觸發時立即彈出**。彈窗屬 L2 系統洞察，必須等 M1.2 `BREAKPOINT_DETECTED` 才能浮現，否則破壞深度工作（RISK-04）
- ❌ **不要在低落週使用多巴胺視覺特效**（粒子爆炸、彩帶動畫）。視覺慶祝與情緒低落的落差會加劇使用者的疏離感（R05 §諂媚效應）
- ❌ **不要讓 Wrapped 每週強制顯示（不可跳過）**。Wrapped 是回顧工具，不是問卷；使用者應能隨時關閉，不施加額外認知壓力

## 9. Open Questions

- [ ] **`mood_score_avg` 的計算來源是什麼？** 目前 M6.4 的 `daily_reflections` 尚未定義 `mood_score` 欄位；需確認是 user 自評分、AI 推論、還是兩者平均
- [ ] **月度 Wrapped 和週度 Wrapped 的格式是否相同？** 月度的資料量更大，是否需要多張卡片（swipeable）而非單一文字敘事？
- [ ] **連續低落的「支持資源」連結指向哪裡？** 系統外部資源（心理諮商熱線）還是 coOS 內部的 Persona？需要倫理審查
- [ ] **Wrapped 是否需要分角色顯示？** 例如「資工系大學生」角色本週 vs「家庭成員」角色本週，分開呈現還是合併？

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 單一職責：敘事化週期回顧
- [x] §2 至少 4 個 `Rxx §章節` 引用（R10×2, R05, R01）
- [x] §3 Schema 含輸入的情緒指標欄位
- [x] §4 依賴是真實模組編號（含 M1.2 Defer 依賴）
- [x] §5 RISK-10、RISK-04 標注，加自定義連續低落風險
- [x] §6 測試覆蓋三種 mood 級距 + Defer 機制 + 低落週無特效
- [x] §8 至少 4 條反模式含情緒設計理由
- [x] §9 至少 4 個開放問題（含 mood_score 欄位定義缺口）
