# M3.4 — 沉浸式多智能體幫手模組 (Multi-Agent AI Helper)

**標籤**:`[MVP]`
**版本**:`1.1`
**最後更新**:2026-06-03

## 1. Purpose

作為使用者與多智能體系統的核心輸入介面,以「雙軌制側邊欄 + 動態配對控制器 + 多模態輸入」讓使用者在同一個對話視圖中與「工具型 AI」或「擬真人設專家」自然互動,並透過隱形自動化提示讓後端 Observer 的萃取動作對使用者可見但不打斷。

### 1.1 線框圖對應 (軟體介面構想.pdf §5 對話系統專家主頁 + §6 對話系統)

PDF 原稿定義**兩種視圖**,以左側邊欄統一導覽:

**版本一 — 專案脈絡視圖** (PDF §5 版本一):

```text
┌─────────────────┬──────────────────────────────────────────────────────┐
│ 🤖 AI 幫手      │  project   📄 內在動機探索                           │
│─────────────────│  intention  找尋探索方法,讓生活更有目標              │
│ [家庭諮商師 品安]│  summary    (AI 自動填入摘要)                        │
│ [動力導師 Robert]│  note       (AI / 使用者筆記)                        │
│ [情感諮商師 Beth]│                                                      │
│ [焦慮治療師 佑棋]│  Event ─●──●──05-18──●──● Milestone  [+/-]        │
│                 │  (里程碑水平時間軸,可縮放)                           │
│   [配對]        │                                                      │
└─────────────────┴──────────────────────────────────────────────────────┘
```

**版本二 — 歷史互動時間軸視圖** (PDF §5 版本二):

```text
┌─────────────────┬──────────────────────────────────────────────────────┐
│ 🤖 AI 幫手      │  timeline        project         intention           │
│─────────────────│  ● 2026-05-03    📄 隨手問        (空白)             │
│ [資工系學長 Terry]│  ● 2026-05-01   📄 三角函數微分  - 詢問sin cos推導  │
│ [微積分助教 宏軒]│ (選取中,斜線陰影)│               - 搞懂正負號        │
│ [資料結構助教育敏]│  ● 2026-04-28   ...                                │
│                 │  ● 2026-04-25   ...                                  │
│   [配對]        │                                                      │
└─────────────────┴──────────────────────────────────────────────────────┘
```

**版本三 — 即時對話視圖** (PDF §6 對話系統):

```text
┌─────────────────┬──────────────────────────────────────────────────────┐
│ 🤖 AI 幫手      │  Session 2026-05-03                                  │
│─────────────────│  [🧑‍💻] 哈囉同學,我是學長宏軒                         │
│ [資工系學長 Terry]│  [🧑‍💻] 以前我在讀微積分時...                         │
│ [微積分助教 宏軒]│  [🧑‍💻] 你打算如何規劃?                               │
│ (選取中,斜線陰影)│                      [👤] 學長好,我打算以成果...    │
│ [資料結構助教育敏]│                                                     │
│                 │  ── Project 偵測為「初始目標設定」創立 ──            │
│   [配對]        │  [+][🔗][workflow▸]  [___輸入框___]          [▷]   │
└─────────────────┴──────────────────────────────────────────────────────┘
```

**UI 細節說明**:

- **左側邊欄 Persona 清單**: 每列顯示`[圓形頭像] 職稱 姓名`。**初始角色開通時，此清單為空，僅顯示「🤖 AI 幫手」**。僅有在解鎖條件觸發（AI 幫手聊天時的推薦通知、背景 telemetry 意圖觸發、或手動配對）並經使用者確認配對後，對應的 Persona 分頁才會顯示於側邊欄中。選取中的 Persona 以斜線陰影標示 (active state)
- **`[配對]` 按鈕**: 固定在側邊欄底部;點擊後開啟狀態輸入彈窗。**不允許直接點擊尚未配對解鎖的 Persona 開啟對話**。
- **歷史時間軸三欄**: `timeline`(日期) / `project`(主題文件圖示+名稱) / `intention`(發問意圖要點);縱向排列由近到遠
- **即時對話**: AI 訊息靠左帶頭像,使用者訊息靠右帶頭像;碎塊發言 (多個獨立 bubble) 模擬真人打字節奏
- **系統通知**: 置中灰色細線文字 (e.g. "Project 偵測為『初始目標設定』創立"),不使用 Modal/Toast
- **輸入區按鈕**: `[+]` 附件、`[🔗]` 網址、`[workflow▸]` 觸發 M3.6 彈窗、右側 `[▷]` 送出
- **專案脈絡區欄位**: `project` (文件圖示+名稱)、`intention` (意圖文字)、`summary` (AI 摘要,自動更新)、`note` (備忘)


### 1.2 Persona 管理 UI（v1.1 新增）

側邊欄除了顯示 Persona 清單，還提供每個 Persona 的行內管理操作：

```text
┌─────────────────────────────────────────────────────┐
│ 🤖 AI 幫手                          [⚙ 管理角色]   │
│─────────────────────────────────────────────────────│
│  🔧  工具型 AI                                      │ ← 永遠置頂，不可刪除
│─────────────────────────────────────────────────────│
│  🎓  微積分助教 宏軒          ✏️  🗑️              │
│  💼  資工系學長 Terry          ✏️  🗑️              │
│  💬  動力導師 Robert           ✏️  🗑️              │
│─────────────────────────────────────────────────────│
│  [+ 配對新專家]      [🔄 對目前專家重新配對]        │
└─────────────────────────────────────────────────────┘
```

**操作行為規範**：

- **`✏️` 編輯**：開啟 `PersonaEditModal`，可修改 `name`、`domain_keywords`（路由觸發詞）、`tone_default`、`avatar_url`；`personality_prompt` 不開放直接編輯（防越權注入）
- **`🗑️` 刪除**：
  - 若此角色下尚有其他 active Persona → 二次確認後軟刪除（`is_active = false`），對應 `role_router_rules` 自動設為 `inactive`
  - 若此為最後一個 Persona → [RISK-17] 顯示強制 warning 彈窗：「刪除後此角色將暫時只有工具型 AI，建議先配對新專家再刪除。」使用者需輸入確認文字後才可執行
- **`[+ 配對新專家]`**：開啟 `MatchPersonaModal`，走 M4.1 §7.5 配對流程狀態機（rule 比對 → LLM 新建 → 使用者預覽確認）
- **`[🔄 重新配對]`**：對當前 active Persona 開啟配對彈窗，並帶入 `exclude_persona_id` 參數，要求 LLM 生成**不同風格**的替代 Persona

**配對彈窗欄位**（`MatchPersonaModal`）：

```text
┌────────────────────────────────────────────────┐
│  為「CSIE」角色配對新的 AI 專家                  │
│                                                │
│  目前情境 context                              │
│  ┌────────────────────────────────────────┐   │
│  │ 我最近在準備期末考，微積分還沒搞懂泰勒展開  │   │
│  └────────────────────────────────────────┘   │
│                                                │
│  你需要什麼類型的專家 description             │
│  ┌────────────────────────────────────────┐   │
│  │ 需要一個有耐心、會用例子解釋的老師       │   │
│  └────────────────────────────────────────┘   │
│                                                │
│  關聯專案（選填）           [內在動機探索 ▼]   │
│                                                │
│  [取消]                    [送出配對請求]      │
└────────────────────────────────────────────────┘
```

配對請求送出後：

1. 後端走 M4.1 §7.5 rule 比對，若匹配度 ≥ 0.80 則直接激活現有 Persona
2. 若無匹配，LLM 生成新 Persona spec，前端顯示 **PersonaPreviewModal**（使用者可編輯名稱後確認）
3. 使用者確認後，呼叫 `POST /api/m6_2/experts/confirm`，正式建立並激活

**Observer 自動推薦入口**：

當 M4.6 Observer 偵測到對話涉及當前 Role 下沒有對應 Persona 的新領域時（例如在 CSIE 角色下談到「論文寫作」），前端在側邊欄底部顯示推薦 chip：

```text
  💡 偵測到「論文寫作」相關討論
     要為 CSIE 配對一位研究導師嗎？  [配對]  [×]
```

點擊 `[配對]` 後預填 context 欄位，走相同配對流程。

## 2. References

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R03 | §1 微觀認知架構 | Persona 側邊欄佈局:工具型 AI 與擬人設專家的雙軌架構 |
| R05 | §治療同盟建構 | 動態配對控制器:不直接選人設,透過「描述狀態」引發配對儀式感 |
| R09 | §6.1 MAS 多智能體系統 | LangGraph MAS 的前端呈現邊界 |
| R09 | §第四章 SDT | 「配對」流程設計必須讓使用者感到「是我選的」(自主) |
| R10 | §語音處理級聯架構 | M3.4.3.3 語音意識流輸入的前端處理 |
| R01 | §DDA 與 PCG | M3.4.4.2 Endowed Progress Effect:非零初始進度條 |

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| 使用者鍵盤輸入 | `string` | `"我想了解 OpenStack 怎麼部署"` |
| 使用者上傳 PDF/圖片 | `File` | PDF 附件 |
| 使用者貼上網址 | `string` (URL) | `"https://docs.openstack.org/..."` |
| 使用者語音 | `AudioBlob` | 麥克風錄製音頻 |
| M4.1 路由決策 (via SSE) | `{ persona_id, route_reason }` | `{ persona_id: "robert_001" }` |
| M4.6 Observer 萃取事件 (via SSE) | `{ type: "PROJECT_CREATED", project_name }` | `{ type: "PROJECT_CREATED", project_name: "OpenStack 實驗" }` |
| M3.1 `activeExpert` | `Expert { id, expertName }` | `{ id: "robert_001", expertName: "Robert" }` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| `POST /api/m4_1/chat` | `{ thread_id, content, role: "user", attachments?: [] }` | 對話訊息 |
| `POST /api/m4_1/match_persona` | `{ current_state_description: string }` | 配對請求 |
| `raw_tracking_logs` (M0.4) | `{ source: "M3.4", event: "message_sent", thread_id }` | 觀測 |
| M3.1 `setActiveExpert` action | `expert_id: string` | 配對完成後更新全域狀態 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M3.1** (全域狀態):提供 `activeExpert`、`currentRole`
- **M4.1** (Agent 路由管線):對話請求的後端入口
- **M4.6** (Observer Agent):背景萃取事件透過 SSE 推送到 M3.4 顯示隱形提示

### 下游 (誰依賴我)

- **M4.2** (擬真人設狀態機):M3.4 輸入的對話訊息是 M4.2 的觸發資料
- **M3.6** (工作流彈窗):由 M3.4 的 `[workflow]` 按鈕喚出

## 5. Known Risks

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-11** | 語音輸入走本地 Whisper 可能耗盡 RAM | M3.4.3.3 語音按鈕送出後必須先查 RAM,走 `VoiceTranscriptionRouter` 三級降級;前端顯示「語音處理中」而非直接送出 |
| **RISK-04** | Observer 萃取事件的隱形提示若直接彈出通知會破壞深度工作 | 隱形提示必須使用 L2 defer 通道:非 `BREAKPOINT_DETECTED` 時,提示僅更新側邊欄 Badge,不彈 Modal |
| **RISK-12** | 使用者貼上的網址若含敏感內容直接上雲 | 網址內容必須先經 M2.3 Eguard 過濾,只取標題與摘要;原始 URL 本地記錄,不上雲 LLM |
| **RISK-16** | LLM 新建的 Persona 首次上場無歷史，ARPM 無基準可比對 → 人設不穩定 | 確認新建後由 `create_persona_with_seed` 自動生成種子對話；前端 PersonaPreviewModal 完成後才解除 `is_loading` 狀態，確保種子對話已就緒再開放對話輸入框 |
| **RISK-17** | 刪除最後一個 Persona 後 Router 白名單空集合 → 靜默降級為工具型 AI | 前端 `🗑️` 守門員：若為最後一個 active Persona，必須顯示強制 warning 彈窗並要求輸入確認文字；刪除後後端廣播 `EXPERT_POOL_EMPTY` SSE，前端顯示「暫無配對專家」引導文案 |

## 6. Acceptance Criteria

```typescript
// tests/m3_4/multi_agent_helper.test.ts

describe("M3.4.1 雙軌側邊欄", () => {
  it("側邊欄第一位永遠是工具型 AI,且無人設標籤", () => {
    // 預設 active_experts 為空，僅載入工具型 AI
    render(<ExpertSidebar activeExperts={[]} allExperts={mockExperts} />);
    const items = screen.getAllByTestId("expert-item");
    expect(items.length).toBe(1);
    expect(items[0]).toHaveAttribute("data-type", "tool");
  });

  it("當專家解鎖後，該擬真人設專家才會顯示在側邊欄，顯示職稱與姓名", () => {
    // 傳入已解鎖的 activeExperts 清單
    const activeExperts = [{ id: "robert_001", expertName: "Robert", title: "動力導師", domain: "motivation" }];
    render(<ExpertSidebar activeExperts={activeExperts} allExperts={mockExperts} />);
    const items = screen.getAllByTestId("expert-item");
    expect(items.length).toBe(2); // 1 個工具型 AI + 1 個解鎖的專家
    expect(items[1]).toHaveAttribute("data-type", "persona");
    expect(items[1]).toHaveTextContent("動力導師");
    expect(items[1]).toHaveTextContent("Robert");
  });
});


describe("M3.4.2 動態配對控制器", () => {
  it("直接點選清單中的 Persona 無法啟動對話,必須透過配對流程", () => {
    render(<ExpertSidebar experts={mockExperts} />);
    const personaItem = screen.getAllByTestId("expert-item")[1];
    fireEvent.click(personaItem);
    // 不應直接開啟對話,應提示「請透過配對按鈕」
    expect(screen.queryByTestId("chat-input")).not.toBeInTheDocument();
    expect(screen.getByTestId("match-required-hint")).toBeInTheDocument();
  });

  it("點擊『配對』按鈕後顯示狀態輸入彈窗", () => {
    render(<MatchPersonaButton />);
    fireEvent.click(screen.getByTestId("match-btn"));
    expect(screen.getByTestId("match-state-modal")).toBeInTheDocument();
  });

  it("『重新配對』送出當前狀態並分配風格不同的新 Persona", async () => {
    const matchSpy = vi.fn().mockResolvedValue({ persona_id: "beth_002" });
    render(<MatchPersonaButton onMatch={matchSpy} currentPersonaId="robert_001" />);
    fireEvent.click(screen.getByTestId("rematch-btn"));
    fireEvent.change(screen.getByTestId("state-input"), {
      target: { value: "我需要更嚴格的導師" },
    });
    fireEvent.click(screen.getByTestId("confirm-match-btn"));
    await waitFor(() => {
      expect(matchSpy).toHaveBeenCalledWith(
        expect.objectContaining({ exclude_persona_id: "robert_001" })
      );
    });
  });
});

describe("M3.4.3 多模態輸入區", () => {
  it("PDF 上傳後顯示檔案名稱預覽", async () => {
    const file = new File(["pdf content"], "report.pdf", { type: "application/pdf" });
    render(<MultimodalInputBar />);
    const input = screen.getByTestId("file-upload-input");
    fireEvent.change(input, { target: { files: [file] } });
    await waitFor(() => {
      expect(screen.getByTestId("attachment-preview")).toHaveTextContent("report.pdf");
    });
  });

  it("[RISK-11] 語音按鈕點擊後走 VoiceTranscriptionRouter,不直接送出", async () => {
    const routerSpy = vi.fn().mockResolvedValue({ transcript: "我想做 OpenStack" });
    render(<MultimodalInputBar voiceRouter={routerSpy} />);
    fireEvent.click(screen.getByTestId("mic-btn"));
    // 模擬錄音結束
    await waitFor(() => {
      expect(routerSpy).toHaveBeenCalled();
    });
    // 轉錄結果填入輸入框,不直接送出
    expect(screen.getByTestId("chat-input")).toHaveValue("我想做 OpenStack");
  });
});

describe("M3.4.4 隱形自動化與進展效應", () => {
  it("Observer PROJECT_CREATED 事件在側邊欄顯示隱形提示,不彈 Modal", async () => {
    const { emitSSE } = setupSSEMock("/api/m4_6/events");
    render(<MultiAgentHelper />);
    emitSSE({ type: "PROJECT_CREATED", project_name: "OpenStack 實驗" });
    await waitFor(() => {
      expect(screen.getByTestId("system-event-hint")).toBeInTheDocument();
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument(); // 沒有 Modal
    });
  });

  it("[R01 §DDA] 新建專案時初始進度條為非零值 (Endowed Progress)", async () => {
    render(<ProjectCard project={mockNewProject} />);
    const progressBar = screen.getByTestId("project-progress");
    const value = parseInt(progressBar.getAttribute("aria-valuenow") ?? "0");
    expect(value).toBeGreaterThan(0);
  });
});
```

## 7. Implementation Notes

### 7.1 子模組結構

```text
apps/web/src/components/m3_4_ai_helper/
  ├── ExpertSidebar/               # M3.4.1
  │   ├── index.tsx
  │   └── ExpertItem.tsx
  ├── MatchPersonaButton/          # M3.4.2
  │   ├── index.tsx
  │   └── MatchStateModal.tsx
  ├── MultimodalInputBar/          # M3.4.3
  │   ├── index.tsx
  │   ├── FileAttachmentPreview.tsx
  │   └── useVoiceInput.ts         # [RISK-11] 語音三級降級
  ├── ChatMessageList/
  │   ├── index.tsx
  │   └── SystemEventHint.tsx      # M3.4.4.1 隱形提示
  └── ProjectCard/                  # M3.4.4.2 Endowed Progress
      └── index.tsx
```

### 7.2 配對流程 (M3.4.2)

```typescript
// [R05 §治療同盟] 配對不是選人,是「描述你的狀態讓系統推薦」
async function initiateMatch(stateDescription: string, excludePersonaId?: string) {
  const response = await fetch("/api/m4_1/match_persona", {
    method: "POST",
    body: JSON.stringify({
      current_state_description: stateDescription,
      current_role_id: useCoOSStore.getState().currentRole?.id,
      exclude_persona_id: excludePersonaId, // 重新配對時排除原 Persona
    }),
  });
  const { persona_id } = await response.json();
  useCoOSStore.getState().setActiveExpert(persona_id);
}
```

### 7.3 語音輸入三級降級 (M3.4.3.3 — RISK-11)

```typescript
// [R10 §語音處理 + RISK-11] 根據 RAM 動態選擇轉錄方式
export async function useVoiceInput(): Promise<string> {
  const available = await getAvailableRAM();
  if (available > 3 * GB) {
    return localWhisperBase(audioBlob);       // 最高精度,39M params
  } else if (available > 1.5 * GB) {
    return localWhisperTiny(audioBlob);       // 降精度
  } else if (userConsents.voice_cloud) {
    return cloudWhisperWithConsent(audioBlob); // 需明確同意
  } else {
    return queueForLater(audioBlob);           // 排隊等斷點處理
  }
}
```

### 7.4 隱形提示渲染 (M3.4.4.1)

```typescript
// [R09 §6.1 MAS] Observer 萃取事件只更新側邊 Badge,不中斷對話
function SystemEventHint({ event }: { event: ObserverEvent }) {
  const messages: Record<string, string> = {
    PROJECT_CREATED: `Project 偵測為「${event.project_name}」已建立`,
    GOAL_INFERRED: `目標「${event.goal}」已記錄`,
  };
  // [RISK-04] L2 defer: 只顯示於側邊欄,不彈 Modal
  return (
    <div data-testid="system-event-hint" className="system-event-hint-inline">
      {messages[event.type] ?? event.type}
    </div>
  );
}
```

### 7.5 Endowed Progress Effect (M3.4.4.2)

```typescript
// [R01 §DDA 建構性基元] 非零初始進度條強化 Goal Gradient 效應
function computeInitialProgress(project: NewProject): number {
  // 使用者描述了狀態 → 至少 10% 進度
  // 已設定截止日期 → +5%
  // 有關聯任務 → +每個任務 3%
  let progress = 10;
  if (project.deadline) progress += 5;
  progress += Math.min(project.tasks?.length ?? 0, 10) * 3;
  return Math.min(progress, 30); // 初始不超過 30%
}
```

### 7.6 異常處理

- SSE 連線斷線 → 顯示連線中斷 Badge,不清空對話歷史;重連後補齊遺漏事件
- 語音轉錄失敗 → 顯示「語音轉錄失敗,請改為文字輸入」,不靜默失敗
- 配對 API 無法回傳 persona_id → 退化為「工具型 AI」,並提示「目前使用工具模式,稍後可重新配對」

## 8. Anti-patterns

- ❌ **不要允許使用者直接從清單點選 Persona 開始對話**。配對流程的「描述狀態」是建立治療同盟的入場儀式 (R05 §治療同盟);繞過它等於繞過 M4.2 的 Persona 初始化邏輯
- ❌ **不要讓 Observer 事件以 Modal 或 Toast 彈出**。Observer 是背景服務;隱形提示必須沉默嵌入側邊欄,高認知負荷下不應奪取焦點 (RISK-04)
- ❌ **不要讓語音錄音直接上雲端 Whisper API**,除非有明確的 `user.privacy_consent_voice_cloud = true`。語音內容含使用者意識流,屬 L1 明文 (RISK-11)
- ❌ **不要讓新建專案的初始進度條顯示 0%**。0% 在心理上等於「從零開始」,會觸發起始抵制;非零初始值啟動 Goal Gradient 效應 (R01 §DDA)

## 9. Open Questions

- [ ] **雙軌側邊欄的工具型 AI 與 Persona AI 是否可以同時顯示在同一對話窗口中?** 還是切換式?目前 M3.4.1.x 設計為切換,但「工具 + 人設同框」是否有 UX 價值?
- [ ] **配對流程中,使用者描述的「當前狀態」是否要存入 DB?** 若存入,屬 L1 明文資料,後續如何使用?
- [ ] **語音意識流轉錄後的原始文字是否顯示在輸入框讓使用者確認,還是直接送出?** 目前 SPEC 設計為「填入輸入框確認」,但若使用者對著螢幕說話習慣不同,是否需要選項?
- [ ] **網址內容預覽的深度是多少?** 只取 OG metadata,還是完整爬取頁面文字給 LLM?後者涉及 L1/L2 隱私分層

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 單一職責:核心輸入介面
- [x] §2 至少 6 個 `Rxx §章節` 引用
- [x] §3 Schema 完整,含多模態輸入類型
- [x] §4 依賴是真實模組編號
- [x] §5 RISK-04、RISK-11、RISK-12 均標注
- [x] §6 測試涵蓋四個子模組
- [x] §8 至少 4 條反模式含研究引用
- [x] §9 至少 4 個開放問題
