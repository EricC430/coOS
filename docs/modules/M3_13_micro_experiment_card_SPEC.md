# M3.13 — 小實驗卡 (Micro-Experiment Card)

**標籤**:`[進階]`
**版本**:`1.0` / `draft`
**最後更新**:2026-10-19
**設計來源**:`docs/M5_ICEBERG_REDESIGN.md` §5.1 mode 9、§8.3
**動工前提**:`docs/MVP_CLOSURE_REPORT.md` 存在

## 1. Purpose (目的)

在儀表板呈現系統提議的一個小行動,讓使用者自主決定要不要試,並在結果出來後**只陳述觀察到的事實**,把「這代表什麼」留給使用者自己說。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R23 | §實驗設計 | 預測 → 行動 → 觀察 → 反思;卡片負責行動與觀察,反思交給專家對話 |
| R09 | §第四章 SDT | 自主性:接受 / 不要 / 換一個 三個選項等價呈現 |
| R25 | §實驗結果 | 結果卡不下結論,邀請使用者自己說 |
| R08 | §二 任務斷點打斷管理 | 結果出爐不即時彈出,等斷點或下次打開儀表板 |

## 3. Inputs / Outputs

### Inputs (本地 sidecar)

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| `GET /api/m5_5/experiments/active?role_id=` | `ExperimentCard[]` | 見 §7.2 |
| SSE `m5_5.experiment_updated` | `{experimentId, status}` | `{status:"observed"}` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `POST /api/m5_5/experiments/{id}/respond` | `{action: "accept" \| "decline" \| "swap"}` | → M5.5 生命週期 |
| `POST /api/m5_5/experiments/{id}/debrief` | — | 開啟該角色專家對話,M5.5 排 `EXP_DEBRIEF` |

## 4. Dependencies

### 上游 (我依賴誰)

- **M5.5**:實驗提議與狀態
- **M3.2**:儀表板版位
- **M3.4**:「想聊聊」開啟專家對話
- **M1.2**:結果卡的顯示時機

### 下游 (誰依賴我)

- **M5.5**:使用者的接受 / 婉拒 / 換一個

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-22 | 遊戲化強化冰山 | 卡片無 XP、無進度條、無連續天數、無「失敗」字樣 |
| RISK-01 | 草稿核准 / IKEA | 卡片不替使用者寫反思;「想聊聊」只開啟對話 |
| RISK-04 | 斷點 vs 即時 | 結果更新不彈出 modal,只在卡片上靜態更新 |
| RISK-12 | 社群側通道 | 無分享按鈕;實驗內容不進任何社群貼文草稿 |

## 6. Acceptance Criteria (驗收標準)

```typescript
// tests/m3_13/experiment_card.test.tsx

describe("M3.13.1 提議卡", () => {
  it("三個選項等價呈現 (同尺寸、同層級)", async () => {
    render(<ExperimentCard experiment={proposed} />);
    const btns = ["exp-accept", "exp-decline", "exp-swap"].map((id) => screen.getByTestId(id));
    const classes = new Set(btns.map((b) => b.dataset.variant));
    expect(classes.size).toBe(1);
  });

  it("婉拒後卡片收起,不出現任何挽留或可惜文案", async () => {
    render(<ExperimentCard experiment={proposed} />);
    fireEvent.click(screen.getByTestId("exp-decline"));
    await waitFor(() => expect(screen.queryByTestId("experiment-card")).toBeNull());
    expect(document.body.textContent).not.toMatch(/可惜|確定嗎|錯過/);
  });

  it("每週最多換 2 次,之後換一個按鈕停用並說明", async () => {
    render(<ExperimentCard experiment={{ ...proposed, swapsLeftThisWeek: 0 }} />);
    expect(screen.getByTestId("exp-swap")).toBeDisabled();
  });
});

describe("M3.13 遊戲化隔離 (RISK-22)", () => {
  it("卡片任何狀態都不出現 XP、分數、進度條、連續天數", () => {
    for (const status of ["proposed", "in_progress", "observed", "not_observed", "expired"] as const) {
      const { container, unmount } = render(<ExperimentCard experiment={{ ...proposed, status }} />);
      expect(container.textContent).not.toMatch(/XP|分數|連續|天連勝|失敗/);
      expect(container.querySelector("[role=progressbar]")).toBeNull();
      unmount();
    }
  });
});

describe("M3.13.3 結果卡", () => {
  it("observed 只陳述事實並提供想聊聊", () => {
    render(<ExperimentCard experiment={observed} />);
    expect(screen.getByTestId("exp-observation")).toHaveTextContent("10/21");
    expect(screen.getByTestId("exp-debrief")).toBeInTheDocument();
    expect(screen.getByTestId("experiment-card").textContent).not.toMatch(/你做到了!|證明|成長/);
  });

  it("not_observed 不責備,提供收起與想聊聊", () => {
    render(<ExperimentCard experiment={notObserved} />);
    expect(screen.getByTestId("experiment-card").textContent).not.toMatch(/沒做到|失敗|可惜/);
  });

  it("狀態更新不彈出 modal", async () => {
    render(<Dashboard />);
    emitSSE("m5_5.experiment_updated", { experimentId: "e1", status: "observed" });
    await flush();
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

```
apps/desktop/src/components/m3_13_micro_experiment/
├── ExperimentCard.tsx        # 依 status 切換三種呈現
├── ProposalView.tsx          # M3.13.1
├── InProgressView.tsx        # M3.13.2
└── ResultView.tsx            # M3.13.3
```

放在 M3.2 儀表板的次要欄 (不佔主時間軸),同時最多顯示 2 張 (對應 M5.5 全域上限)。

### 7.2 資料結構

```typescript
type ExperimentStatus = "proposed" | "in_progress" | "observed" | "not_observed" | "expired";

interface ExperimentCard {
  experimentId: string;
  roleId: string;
  status: ExperimentStatus;
  proposalText: string;        // M5.5 產生,不含術語,例:「這週試一次:卡超過 30 分鐘,就發一則問題給同學或老師。」
  why?: string;                // 可選的一句動機,例:「看看開口之後會發生什麼。」(不提信念本身)
  expiresAt: string;           // 7 天
  observation?: {              // 只在 observed 時存在
    occurredAt: string;
    factText: string;          // 例:「10/21 14:05 你在 GitHub 發了一則 issue 留言。」
  };
  swapsLeftThisWeek: number;
}
```

### 7.3 文案原則

| 狀態 | 標題 | 內文 | 動作 |
| ---- | ---- | ---- | ---- |
| proposed | 要不要試一個小實驗? | `proposalText` + `why` | 好,試試看 · 這次不要 · 換一個 |
| in_progress | 小實驗進行中 | `proposalText` + 「到 {expiresAt} 為止,不用刻意記錄,coOS 會自己注意到。」 | 收起 |
| observed | 有看到一些事 | `observation.factText` | 想聊聊 · 收起 |
| not_observed / expired | 這次的小實驗結束了 | 「這週沒有看到相關的紀錄,沒關係。」 | 想聊聊 · 收起 |

`observation.factText` 只能包含:時間、行為、可觀察的結果 (例:對方回覆的時間)。**不可**包含評價 (「很棒」)、推論 (「這證明你…」) 或信念 (「求助不等於無能」) —— 意義由使用者在對話中自己說出 [R25: 生成效應 §實驗結果]。

### 7.4 視覺

遵循 `docs/BRAND_GUIDE.md`。卡片為 `card` 底、`amber` 細邊框;三個按鈕同一 variant (例:outline),不使用主要色強調「接受」—— 避免以視覺引導代替選擇。無圖示化的獎勵元素 (星星、火焰、獎盃)。

### 7.5 異常處理

- sidecar 不可達 → 卡片不顯示 (不顯示快取的舊實驗)
- SSE 斷線 → 下次打開儀表板時重新拉取
- 使用者已關閉 M5 (暫停 / 撤回同意) → 進行中的實驗標為 expired,卡片收起

## 8. Anti-patterns (反模式)

- ❌ 不要給實驗 XP、徽章、連續天數或進度條 (RISK-22;外在獎勵會讓實驗變成任務)
- ❌ 不要在結果卡寫「你做到了!」「這證明…」(替使用者下結論,破壞生成效應)
- ❌ 不要把「接受」做成主要按鈕、把「不要」做成灰色小字 (操弄選擇,違反 SDT 自主性)
- ❌ 不要在結果出爐時彈出 modal 或推播 (R08 §二)
- ❌ 不要在卡片上提及使用者的信念或冰山理解

## 9. Open Questions

- [ ] 「換一個」是否應讓使用者看到 2–3 個候選自己挑?(自主性更高,但多一次決策負擔) —— 建議 P4 先做單一替換,觀察換一個的使用率後再決定

---

## SPEC 撰寫 Checklist

- [x] §1 單一職責
- [x] §2 至少 1 個 Rxx 引用
- [x] §3 Schema 為 TypeScript
- [x] §4 依賴為真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼
- [x] §8 ≥3 條反模式
- [x] §9 ≥1 個開放問題
