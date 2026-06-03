# M3.3 — 日報與反思模組 (Daily Report & Reflection)

**標籤**:`[MVP]`
**版本**:`1.0`
**最後更新**:2026-06-03

## 1. Purpose

以時間軸形式呈現每日任務進度,並透過「草稿核准彈窗」強制使用者完成結構化反思後才能獲得 XP——使日報從被動的記錄工具轉型為主動的認知加工環節,讓「我完成了這件事」的 XP 是使用者自己掙來的。

> ⚠️ **M3.3.3 草稿核准彈窗是 coOS 最重要的心理機制之一**。任何省略強制留白欄位的改動都是破壞 IKEA 效應的反模式。

### 1.1 線框圖對應 (軟體介面構想.pdf §2 Daily Report)

PDF 原稿確認以下版面結構:

```text
┌──────────┬──────────────────────────────────────────────────────────────┐
│          │  Daily Report                                        +XP     │
│  2026    │                                                               │
│  MAY     │  ┌─[角色頭像 CSIE]──────────────────────────────────────┐   │
│  16      │  │  📄 微積分作業          學到了～    有違背目標/偏誤?  │   │
│  (時間軸)│  │  ● 正在進行中  花了～時間               reviewed? click│   │
│          │  │  📄 資料結構AI筆記CH2   學到了～    有違背目標/偏誤?  │   │
│  [日曆圖]│  │  ● 已完成      花了～時間               reviewed?     │   │
│          │  └───────────────────────────────────────────────────────┘   │
│          │  ┌─[角色頭像 諮商]──────────────────────────────────────┐   │
│          │  │  📄 聊聊職涯發展         學到了～    有違背目標/偏誤?  │   │
│          │  │  ● 已完成      花了～時間               reviewed?     │   │
│          │  └───────────────────────────────────────────────────────┘   │
└──────────┴──────────────────────────────────────────────────────────────┘
```

**版面細節** (來自 PDF):

- **左側時間軸導覽**: 垂直引導線 + 日期標註 (如 `2026 MAY 16`),底部有日曆圖示作為日期切換錨點;上下滑動切換不同日期
- **右側任務卡片**: 依`角色身分`嚴格分組,每個角色有獨立群組框,群組左側有圓形角色頭像 + 角色名稱 (CSIE / 諮商 等)
- **任務卡片內部結構** (每張):
  - 左上: 文件圖示 + 任務標題 (e.g. "微積分作業")
  - 中: 狀態膠囊 (`正在進行中` / `已完成`) + 耗時 (`花了～時間`)
  - 下: 反思欄 (`學到了～`)
  - 右: 目標對齊檢視 (`有違背目標/偏誤?`) + 互動提示 (`reviewed? click`)
- **右上角**: `+XP` 標示,說明核准後才觸發
- **`reviewed? click`**: 點擊後觸發 M3.3.3 草稿核准彈窗;若已核准則顯示為 `reviewed ✓`

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §四.2 微摩擦力的必要性 | M3.3.3.3 強制留白欄位設計:阻力是 feature,不是 bug |
| R08 | §六.1 IKEA 效應 | M3.3.3 草稿核准機制:使用者親手填寫才觸發心理所有權 |
| R08 | §六.2 吉布斯反思循環 | M3.3.3.2 AI 填補「客觀描述」「初步分析」,使用者完成「感受」「行動」 |
| R08 | §五 意圖脫鉤 | M3.3.2 耗時雙軌載入:優先從 AI 套問,兜底用遙測推算 |
| R10 | §MindScape 反思鷹架 | M3.3.3 架構化反思表單的整體設計 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M3.1 `currentRole` | `{ role_id: string }` | `{ role_id: "csie_001" }` |
| M4.4 深夜草稿排程器 (via API) | `DailyReflection` (draft) | `{ id, date, is_draft: true, ai_description, ai_analysis, user_feeling: null }` |
| M4.4 AI 套問結果 (via API) | `{ task_id, time_spent_minutes: number }` | `{ task_id: "t_abc", time_spent_minutes: 90 }` |
| M1.1 ActivityState 遙測兜底 (via M6.1) | `{ date, app_bucket, duration_minutes }[]` | `[{ app_bucket: "coding", duration_minutes: 120 }]` |
| M3.1 `ROLE_SWITCHED` 事件 | `{ role_id }` | 觸發重新載入該角色的日報列表 |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M4.5 XP 結算守門員 (via API PATCH) | `{ reflection_id, is_reviewed: true, user_feeling, user_action_plan }` | 核准後才呼叫 |
| M6.4 `daily_reflections` 寫入 | `{ user_feeling TEXT, user_action_plan TEXT, is_draft: false, is_reviewed: true }` | 使用者填寫並核准 |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.3", event: "draft_approved", reflection_id }` | 觀測事件 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M3.1** (全域狀態):提供 `currentRole` 以過濾當前角色的日報
- **M4.4** (自然套問與草稿生成器):每日草稿的生產者;AI 套問結果的來源
- **M6.4** (日報反思核心實體):儲存 `daily_reflections` 的持久層

### 下游 (誰依賴我)

- **M4.5** (XP 自動結算引擎):M3.3.3 核准觸發 `is_reviewed = true` 才允許 XP 發放
- **M6.4**:M3.3.3 寫回使用者填寫的欄位

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-01** | M4.5 XP 自動結算在草稿未核准前就發放 Earned XP | M3.3.3 核准按鈕才呼叫 `PATCH /api/m4_5/grant_xp`；M4.5 後端守門員必須拒絕 `is_draft=true` 的請求 |

## 6. Acceptance Criteria

```typescript
// tests/m3_3/daily_report.test.ts

describe("M3.3.1 雙維度時間軸與角色分組", () => {
  it("時間軸任務卡片依 role_id 嚴格分組,不跨組顯示", () => {
    render(<DailyTimeline reflections={mockReflections} currentRole="csie_001" />);
    const cards = screen.getAllByTestId("task-card");
    cards.forEach((card) => {
      expect(card).toHaveAttribute("data-role-id", "csie_001");
    });
  });

  it("日期滑動切換後正確載入對應日期的任務卡片", async () => {
    render(<DailyTimeline />);
    fireEvent.click(screen.getByTestId("date-nav-prev"));
    await waitFor(() => {
      expect(screen.getByTestId("timeline-date-label")).toHaveTextContent(
        formatDate(subDays(new Date(), 1))
      );
    });
  });
});

describe("M3.3.2 寬容耗時卡片", () => {
  it("AI 套問結果可用時,優先顯示套問耗時", async () => {
    server.use(
      rest.get("/api/m4_4/time_spent/:taskId", (_req, res, ctx) =>
        res(ctx.json({ time_spent_minutes: 90, source: "ai_inquiry" }))
      )
    );
    render(<TimeCard taskId="task_001" />);
    await waitFor(() => {
      expect(screen.getByTestId("time-source-badge")).toHaveTextContent("AI 套問");
      expect(screen.getByTestId("time-value")).toHaveTextContent("90 分");
    });
  });

  it("AI 套問無結果時,兜底顯示 IDE 遙測推算值", async () => {
    server.use(
      rest.get("/api/m4_4/time_spent/:taskId", (_req, res, ctx) =>
        res(ctx.status(404))
      )
    );
    render(<TimeCard taskId="task_001" />);
    await waitFor(() => {
      expect(screen.getByTestId("time-source-badge")).toHaveTextContent("遙測推算");
    });
  });
});

describe("M3.3.3 草稿核准彈窗 — 核心心理機制", () => {
  it("彈窗為獨立覆蓋層 (Modal),不背景自動填寫", () => {
    render(<DraftApproveModal reflection={mockDraft} />);
    // AI 填補欄位已顯示,但使用者欄位空白
    expect(screen.getByTestId("ai-description")).not.toBeEmptyDOMElement();
    expect(screen.getByTestId("user-feeling-input")).toHaveValue("");
    expect(screen.getByTestId("user-action-plan-input")).toHaveValue("");
  });

  it("[RISK-01] 未填 user_feeling 時核准按鈕不可點擊", () => {
    render(<DraftApproveModal reflection={mockDraft} />);
    const submitBtn = screen.getByTestId("approve-btn");
    expect(submitBtn).toBeDisabled();
    fireEvent.change(screen.getByTestId("user-feeling-input"), {
      target: { value: "有點焦慮但完成了" },
    });
    // 仍缺 user_action_plan
    expect(submitBtn).toBeDisabled();
  });

  it("[RISK-01] 填寫所有必填欄位後才可核准,且 PATCH is_reviewed 才呼叫", async () => {
    const patchSpy = vi.fn();
    server.use(
      rest.patch("/api/m4_5/grant_xp", (req, res, ctx) => {
        patchSpy(req.body);
        return res(ctx.json({ granted: true }));
      })
    );
    render(<DraftApproveModal reflection={mockDraft} />);
    fireEvent.change(screen.getByTestId("user-feeling-input"), {
      target: { value: "有點焦慮但完成了" },
    });
    fireEvent.change(screen.getByTestId("user-action-plan-input"), {
      target: { value: "明天先做最難的那題" },
    });
    fireEvent.click(screen.getByTestId("approve-btn"));
    await waitFor(() => {
      expect(patchSpy).toHaveBeenCalledWith(
        expect.objectContaining({ is_reviewed: true })
      );
    });
  });

  it("[R08 §四.2] 強制留白欄位:placeholder 明確告知必填且無預設文字", () => {
    render(<DraftApproveModal reflection={mockDraft} />);
    expect(screen.getByTestId("user-feeling-input")).toHaveAttribute(
      "placeholder",
      expect.stringContaining("必填")
    );
    expect(screen.getByTestId("user-feeling-input")).toHaveValue("");
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

```text
apps/web/src/components/m3_3_daily_report/
  ├── DailyTimeline/           # M3.3.1
  │   ├── index.tsx
  │   └── TimelineDay.tsx      # 單日時間軸
  ├── TimeCard/                # M3.3.2
  │   ├── index.tsx
  │   └── useTimeFallback.ts   # 雙軌兜底邏輯
  └── DraftApproveModal/       # M3.3.3 ⚠️ 核心心理機制
      ├── index.tsx
      ├── GibbsReflectionForm.tsx
      └── useApprovalGuard.ts  # RISK-01 守門員
```

### 7.2 耗時雙軌兜底 (M3.3.2)

```typescript
// [R08 §五 意圖脫鉤] AI 套問結果優先,遙測兜底
export async function resolveTimeSpent(taskId: string): Promise<TimeSpentResult> {
  const aiResult = await fetchAIInquiryTime(taskId).catch(() => null);
  if (aiResult?.time_spent_minutes) {
    return { ...aiResult, source: "ai_inquiry" };
  }
  const telemetryResult = await fetchTelemetryEstimate(taskId);
  return { ...telemetryResult, source: "telemetry_estimate" };
}
```

### 7.3 草稿核准守門員 (M3.3.3 — RISK-01)

```typescript
// [R08 §六.1 IKEA 效應 + RISK-01] 核准前強制驗證
export function useApprovalGuard(reflection: DailyReflection) {
  const isValid =
    reflection.user_feeling.trim().length > 0 &&
    reflection.user_action_plan.trim().length > 0 &&
    reflection.ai_description.length > 0;

  const approve = async () => {
    if (!isValid) throw new Error("validation_failed");
    // 先更新 DB,再呼叫 XP 結算
    await patchReflection(reflection.id, {
      user_feeling: reflection.user_feeling,
      user_action_plan: reflection.user_action_plan,
      is_draft: false,
      is_reviewed: true,
    });
    // [RISK-01] XP 只在 is_reviewed = true 後才請求
    await grantXP(reflection.id);
  };

  return { isValid, approve };
}
```

### 7.4 吉布斯反思循環區塊佈局 (M3.3.3.2)

依吉布斯六個循環階段對應表單欄位:

| 吉布斯階段 | 欄位 | 填寫者 |
| ---------- | ---- | ------ |
| 描述 (Description) | `ai_description` | AI 自動填補 |
| 感受 (Feelings) | `user_feeling` | 使用者**必填** |
| 評估 (Evaluation) | `ai_analysis` | AI 自動填補 |
| 分析 (Analysis) | (含於 `ai_analysis`) | AI |
| 結論 (Conclusion) | `learned_lesson` (選填) | 使用者 |
| 行動計畫 (Action Plan) | `user_action_plan` | 使用者**必填** |

### 7.5 異常處理

- 草稿 API 下線 → 顯示「草稿載入失敗,稍後重試」,不顯示空白彈窗
- 核准 API 失敗 → 保留使用者填寫的欄位內容,顯示重試按鈕,不清空表單
- `daily_reflections` 中 `ai_description` 為空 (AI 草稿排程未執行) → 顯示提示「AI 草稿尚未生成,你也可以先自行填寫」,所有欄位開放手動輸入

## 8. Anti-patterns

- ❌ **絕對不要自動填入 `user_feeling` 或 `user_action_plan`**,即使 AI 有信心的猜測。IKEA 效應的核心在於使用者親手完成 (R08 §六.1);自動填入等於繞過了這個機制
- ❌ **不要在使用者未核准前就呼叫 XP 結算 API**。哪怕只是「預先計算顯示即將獲得多少 XP」都應避免;那會讓使用者感覺 XP 已是囊中物,核准變成形式 (RISK-01)
- ❌ **不要把 DraftApproveModal 做成 inline 表單嵌入時間軸**。必須是全屏覆蓋 Modal,從視覺上切斷使用者與其他 UI 的連結,強制聚焦反思 (R08 §六.2 吉布斯循環)
- ❌ **不要省略「學到了什麼?」的對齊詢問**。M3.3.3.4 嚴格驗證器必須阻擋空白提交,這是 M4.5 守門員的前端第一道防線

## 9. Open Questions

- [ ] **AI 草稿若在深夜 03:00 才生成,使用者早上開啟 App 時的展示順序?** 當日草稿 vs 昨日草稿如何排序?
- [ ] **`learned_lesson` 欄位是選填還是必填?** 目前 M6.4 Schema 未定義此欄位,需確認是否加入
- [ ] **草稿核准後若使用者想修改感受,是否允許?** 修改後是否需要重新結算 XP?
- [ ] **時間軸日期範圍上限是多少天?** 無限捲動還是限制顯示最近 30 天?

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責,包含心理機制說明
- [x] §2 至少 5 個 `Rxx §章節` 引用
- [x] §3 Schema 完整,含 AI 填補 vs 使用者填寫的欄位區分
- [x] §4 依賴是真實模組編號
- [x] §5 RISK-01 標注且緩解策略明確
- [x] §6 測試涵蓋 RISK-01 守門員邏輯
- [x] §8 至少 4 條反模式,含心理機制理由
- [x] §9 至少 4 個開放問題
