# M3.6 — 脈絡內自動化設定彈窗 (In-Context Workflow Modal)

**標籤**:`[MVP]`
**版本**:`1.0`
**最後更新**:2026-06-03

## 1. Purpose

在不脫離對話視圖的前提下,讓使用者能快速綁定外部資料源 (GitHub、Obsidian、瀏覽器日誌) 並設定工作流觸發條件——讓「自動化設定」成為對話的自然延伸,而非跳轉到設定頁面的中斷動作。

### 1.1 線框圖對應 (軟體介面構想.pdf §7 第三方系統連動與觸發)

PDF 原稿顯示此 Modal 由對話框輸入區的 `[workflow▸]` 按鈕向上展開,以綠色箭頭標示觸發路徑:

```text
┌──────────────────────────────────────────────────────────────┐
│                                            chatbot chats     │
│  connect to  github repo / files / websites...               │
│                                                              │
│  trigger by  commit... / period... / keyword...              │
│                                                              │
└──────────────────────────────────────────────────────────────┘
        ↑ (綠色箭頭) 由下方 [workflow▸] 按鈕喚出
```

**版面細節** (來自 PDF):

- **整體形式**: 置中懸浮視窗 (Modal/Overlay),底層可隱約看見對話框,確立「不脫離對話脈絡」的設計
- **觸發路徑標示**: 右上角小字補充 `chatbot chats`,說明此設定同時適用於 AI 對話歷史作為資料來源
- **上半部 — 資料來源綁定區**:
  - `connect to github repo / files / websites...`
  - 三個可選來源 (UI 呈現為 chip/badge 選擇器):
    - `github repo` → OAuth 2.0 授權 (M1.4.1)
    - `files` → 本機 Obsidian Vault 路徑選擇
    - `websites` → 確認 M1.3.2 瀏覽器擴充已安裝
    - `chatbot chats` → 選取後將歷史對話記錄納入 RAG 索引
- **下半部 — 觸發條件設定區**:
  - `trigger by commit... / period... / keyword...`
  - 三種觸發模式 (選擇後動態顯示對應表單欄位):
    - `commit` → GitHub Repo 選擇器 + 可選關鍵字過濾
    - `period` → Cron 語法輸入框 (e.g. `0 3 * * *`) 或視覺化週期選擇器
    - `keyword` → 關鍵字輸入框,對話中偵測到即觸發
- **儲存後的動作 (`action`)**: 對應到後端 `WorkflowTrigger.action`:
  - `create_draft` (建立日報草稿)
  - `send_nudge` (推送微 nudge)
  - `update_project_status` (更新專案進度)

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R10 | §代理工作流狀態機 | 工作流觸發條件的狀態機設計:事件驅動的自動化規則 |
| R08 | §五 意圖脫鉤 | 脈絡內設定 (不跳轉) 降低設定動作的認知成本,維持使用者的對話作者身分 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| 使用者點擊 `[workflow]` 按鈕 | `{ thread_id: string }` | 從 M3.4 對話框觸發 |
| M3.1 `currentRole` | `{ role_id: string }` | 用於將工作流與角色綁定 |
| `GET /api/m1_4/connected_sources` | `DataSource[]` | `[{ type: "github", repo: "user/repo", status: "connected" }]` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `POST /api/m1_4/bind_source` | `{ source_type, config, role_id }` | `{ source_type: "github", config: { repo: "user/repo" }, role_id: "csie_001" }` |
| `POST /api/m1_4/create_trigger` | `{ event_type, condition, action, role_id }` | `{ event_type: "git_commit", condition: { keyword: "fix" }, action: "create_draft" }` |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.6", event: "workflow_configured", source_type }` | 觀測 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M3.4** (AI 幫手模組):提供 `[workflow]` 按鈕的喚出入口與 `thread_id`
- **M3.1** (全域狀態):提供 `currentRole` 將工作流與角色關聯
- **M1.4** (Git 與工作流遙測接收器):工作流後端的實際執行者

### 下游 (誰依賴我)

- **M1.4**:M3.6 設定的觸發條件由 M1.4 在後端執行

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| RISK-12 | GitHub Repo 連結後,若 Webhook 接收的 commit message 含敏感資訊直接上雲 | M1.4 Webhook 接收到的 commit payload 必須先經 M2.3 DRIFT 過濾;M3.6 UI 層明確顯示「僅事件觸發,原始 commit 訊息不上雲 LLM」的提示 |

## 6. Acceptance Criteria

```typescript
// tests/m3_6/workflow_modal.test.ts

describe("M3.6.1 對話框快捷喚出", () => {
  it("點擊 workflow 按鈕後 Modal 出現,不跳轉頁面", () => {
    render(<MultiAgentHelper />);
    fireEvent.click(screen.getByTestId("workflow-btn"));
    expect(screen.getByTestId("workflow-modal")).toBeInTheDocument();
    expect(window.location.pathname).toBe("/"); // 不跳轉
  });

  it("Modal 關閉後對話框焦點自動回到輸入框", async () => {
    render(<MultiAgentHelper />);
    fireEvent.click(screen.getByTestId("workflow-btn"));
    fireEvent.click(screen.getByTestId("modal-close-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("chat-input")).toHaveFocus();
    });
  });
});

describe("M3.6.2 外部資料源綁定 UI", () => {
  it("顯示 GitHub / Obsidian / 瀏覽器日誌三個綁定選項", () => {
    render(<WorkflowModal open={true} />);
    expect(screen.getByTestId("source-github")).toBeInTheDocument();
    expect(screen.getByTestId("source-obsidian")).toBeInTheDocument();
    expect(screen.getByTestId("source-browser")).toBeInTheDocument();
  });

  it("GitHub 綁定成功後顯示已連線 Badge", async () => {
    const bindSpy = vi.fn().mockResolvedValue({ status: "connected" });
    render(<WorkflowModal open={true} onBind={bindSpy} />);
    fireEvent.click(screen.getByTestId("source-github"));
    fireEvent.change(screen.getByTestId("github-repo-input"), {
      target: { value: "user/my-repo" },
    });
    fireEvent.click(screen.getByTestId("connect-github-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("source-github-badge")).toHaveTextContent("已連線");
    });
  });
});

describe("M3.6.3 觸發條件設定表單", () => {
  it("設定 Commit 觸發條件後寫入後端", async () => {
    const createSpy = vi.fn().mockResolvedValue({ id: "trigger_001" });
    render(<WorkflowModal open={true} onCreateTrigger={createSpy} />);
    fireEvent.change(screen.getByTestId("trigger-event-select"), {
      target: { value: "git_commit" },
    });
    fireEvent.change(screen.getByTestId("trigger-keyword-input"), {
      target: { value: "fix" },
    });
    fireEvent.click(screen.getByTestId("save-trigger-btn"));
    await waitFor(() => {
      expect(createSpy).toHaveBeenCalledWith(
        expect.objectContaining({ event_type: "git_commit" })
      );
    });
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

```text
apps/web/src/components/m3_6_workflow_modal/
  ├── index.tsx                    # Modal 容器
  ├── DataSourceBindingPanel.tsx   # M3.6.2
  └── TriggerConditionForm.tsx     # M3.6.3
```

### 7.2 資料源綁定 (M3.6.2)

```typescript
// 三種資料源的連線方式
const SOURCE_CONFIG = {
  github: {
    authMethod: "oauth",                     // M1.4.1 OAuth 流程
    callbackUrl: "/api/m1_4/github/callback",
  },
  obsidian: {
    authMethod: "local_path",                // 使用者選擇本機 Vault 路徑
    callbackUrl: null,
  },
  browser: {
    authMethod: "extension_check",           // 確認 M1.3.2 擴充已安裝
    callbackUrl: null,
  },
};
```

### 7.3 觸發條件狀態機 (M3.6.3)

```typescript
// [R10 §代理工作流狀態機] 觸發條件的結構化表示
interface WorkflowTrigger {
  event_type: "git_commit" | "time_schedule" | "keyword_match";
  condition: {
    keyword?: string;      // 關鍵字篩選
    cron?: string;         // 時間週期 (cron 格式)
    repo?: string;         // GitHub Repo 範圍
  };
  action: "create_draft" | "send_nudge" | "update_project_status";
  role_id: string;         // 工作流隸屬角色
}
```

### 7.4 異常處理

- GitHub OAuth 失敗 → 顯示錯誤說明,不關閉 Modal
- Obsidian 路徑不存在 → 顯示「找不到 Vault,請確認路徑」
- 觸發條件儲存失敗 → 保留表單內容,顯示重試按鈕

## 8. Anti-patterns

- ❌ **不要讓 workflow 按鈕跳轉到獨立設定頁面**。脈絡內設定 (In-Context) 是 M3.6 的核心設計原則 (R08 §五);跳轉頁面等於引入破壞性中斷
- ❌ **不要讓 GitHub Webhook 的 commit 訊息原文出現在 LLM 的 Prompt 中**。必須先過 M2.3 DRIFT (RISK-12)
- ❌ **不要讓工作流跨角色生效**。每個觸發條件必須綁定 `role_id`,不允許「全角色生效」的工作流

## 9. Open Questions

- [ ] **工作流觸發的 `action` 類型是否需要更多選項?** 例如「觸發 Persona 對話」「更新熱圖計數」?
- [ ] **MVP 階段 Obsidian 的寫入方向?** M4.7 是從 coOS 寫出到 Obsidian,M3.6 的「Obsidian 資料源綁定」是反向讀入嗎?兩者方向需確認

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 單一職責:脈絡內設定
- [x] §2 至少 2 個 `Rxx §章節` 引用
- [x] §3 Schema 完整含觸發條件資料結構
- [x] §4 依賴是真實模組編號
- [x] §5 RISK-12 標注
- [x] §6 測試涵蓋三個子模組
- [x] §8 至少 3 條反模式
- [x] §9 至少 1 個開放問題
