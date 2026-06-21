# M1.3.1 — VS Code AST 攔截器擴充

**標籤**: `[MVP]`
**版本**: `1.0 draft`
**最後更新**: 2026-06-01

---

## 1. Purpose (目的)

以 VS Code Extension 形式採集程式碼編輯活動，計算「源碼變更熵」(Shannon Entropy)、人機協作比例、程式碼焦慮死循環（Agent Churn）與檔案停留時間，透過 Local Socket 回傳 Tauri，供下游推論開發者的認知狀態與人機協作節奏。

> 一句話:「**在 AI Agent 時代，從 IDE 內部度量『人機協作度』與『審查/除錯焦慮狀態』，而非單純的打字量**」。

---

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R02 | §源碼變更熵 §1.1 | Shannon Entropy H = -Σ pᵢ log(pᵢ),pᵢ 為各檔案 diff 比例;高熵 = 分散編輯,低熵 = 專注單檔 |
| R02 | §時間動力學 §1.2 | 儲存間距的爆發性特徵:頻繁 Ctrl+S = 焦慮/反覆調試;長間距 = 沉浸/閱讀 |

---

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| VS Code `onDidChangeTextDocument` API | `TextDocumentChangeEvent` | `{ uri: "file:///main.py", changes: [{range, text}] }` |
| VS Code `onDidChangeActiveTextEditor` API | `TextEditor` | `{ document.uri, viewColumn }` |
| VS Code `onDidSaveTextDocument` API | `TextDocument` | `{ uri, languageId, lineCount }` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| Tauri (via Local Socket) → M0.4 → `raw_tracking_logs` | `CodeActivityEvent` | `{ module: "M1.3.1", action: "edit_burst", payload: { entropy: 0.72, files_touched: 3, save_interval_s: 45, human_typed_chars: 120, ai_generated_chars: 850, copilot_ratio: 0.87, churn_index: 0.15 } }` |
| Tauri (via Local Socket) → M0.4 → `raw_tracking_logs` | `FileStayEvent` | `{ module: "M1.3.1", action: "file_stay", payload: { files: ["src/main.py"], stay_s: 1200, lines_changed: 42, stay_mode: "active_review" } }` |
| Tauri (via Local Socket) → M1.2 | `ide_focus_leave` 事件 | `{ module: "M1.3.1", action: "ide_focus_leave" }` — M1.2 以此觸發 `BreakpointType::IDE_FOCUS_LEAVE` |

**CodeActivityEvent TypeScript Interface**:

```typescript
// apps/vscode-extension/src/types.ts
interface CodeActivityPayload {
    entropy: number;           // Shannon Entropy [0,1],5 分鐘滑動視窗
    files_touched: number;     // 視窗內觸碰的不同檔案數
    save_interval_s: number;   // 最近兩次 Ctrl+S 間距 (秒)
    human_typed_chars: number; // 啟發式判定的人類輸入字元數
    ai_generated_chars: number;// 啟發式判定的 AI 生成字元數
    copilot_ratio: number;     // ai_generated_chars / (human + ai) [0,1]
    churn_index: number;       // 5 分鐘內 Agent 死循環指標 [0,1]
}

interface FileStayPayload {
    files: string[];           // 相對工作區路徑列表 (如 ["src/main.py"])
    stay_s: number;            // 停留時間 (秒)
    lines_changed: number;     // 期間變更行數
    stay_mode: "active_edit" | "active_review" | "passive_read";
    file_ext: string;          // 主要檔案副檔名 (如 ".py")
}

interface CodeActivityEvent {
    module: "M1.3.1";
    action: "edit_burst" | "file_stay" | "ide_focus_leave";
    payload: CodeActivityPayload | FileStayPayload | Record<string, never>;
    timestamp: string;         // ISO 8601 UTC
}
```

---

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.2** (Tauri IPC): Local Socket server 由 Tauri Rust 層提供,M1.3.1 是 client;連線目標為 `\\.\pipe\coos_telemetry` (Windows Named Pipe)
- **M0.4** (結構化日誌): 所有事件最終經 M0.4 管線寫入 `raw_tracking_logs`

> ⚠️ **M1.1 不是 M1.3.1 的上游依賴**。M1.3.1 不消費 M1.1 的事件流,兩者共用相同的基礎設施 (M0.2 Named Pipe、M0.4 寫入管線) 但各自獨立採集訊號。M1.3 registry 中的 `Deps: M1.1` 描述的是整個 M1.3 對 M1.1 提供焦點狀態的隱性依賴 (M1.3.2 需要知道前景是否為瀏覽器),而非 M1.3.1 直接消費 M1.1 事件。

### 下游 (誰依賴我)

- **M4.8** (隱性狀態推論): 從 `raw_tracking_logs` 讀取 `entropy` + `save_interval` 推論焦慮/心流 `[R02 §1.1]`
- **M2.2** (Gemma 邊緣推論): 批次讀取編輯事件進行意圖向量壓縮
- **M4.4** (深夜草稿): 統計「今日編輯了哪些檔案類型、總編輯量」

---

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| (無直接 RISK-xx) | VS Code Extension 存取檔案系統 → 可能讀到敏感原始碼 | M1.3.1 讀取原始檔案文字內容 (document.getText()) 作為 `content_raw` 發送至本地後端，僅供本地 LLM (M2.2) 意圖分析與安全審計 (M2.3) 使用；此 L1 明文與相對路徑僅儲存於本地 L1 資料庫，絕不上傳 L3 雲端或外部 Cloud LLM |
| (無直接 RISK-xx) | Local Socket 連線斷開 → 事件丟失 | 本地 buffer 暫存最多 100 個事件;Tauri 恢復後批次回傳;超過 100 則丟棄最舊事件 |

---

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m1_3_1/test_vscode_extension.py

class TestChangeEntropyCalculation:
    def test_single_file_edit_low_entropy(self, ext):
        """驗收條件 1: 單檔編輯 → 熵接近 0"""
        ext.simulate_edits([("main.py", 50)])
        event = ext.last_event()
        assert event.payload["entropy"] < 0.1

    def test_multi_file_edit_high_entropy(self, ext):
        """驗收條件 2: 多檔分散編輯 → 熵接近 1"""
        ext.simulate_edits([("a.py", 10), ("b.py", 10), ("c.py", 10), ("d.py", 10)])
        event = ext.last_event()
        assert event.payload["entropy"] > 0.8

class TestFileStayTracking:
    def test_file_stay_duration_tracked(self, ext):
        """驗收條件 3: 停留在單一檔案 20 分鐘 → 正確記錄"""
        ext.simulate_active_editor("main.py", duration_s=1200)
        event = ext.get_event("file_stay")
        assert event.payload["stay_s"] >= 1200
        assert event.payload["file_ext"] == ".py"

class TestPrivacy:
    def test_relative_file_path_stored_but_absolute_scrubbed(self, ext):
        """驗收條件 4: payload 包含相對檔案路徑,但排除絕對家目錄結構"""
        ext.simulate_edits([("/home/user/secret/src/main.py", 5)])
        event = ext.last_event()
        assert "src/main.py" in event.payload["files"]
        assert "/home" not in str(event.payload["files"])
        assert "secret" not in str(event.payload["files"])

    def test_no_code_content_leaving_local(self, ext):
        """驗收條件 5: L1 明文原始碼僅留在本地 API/LLM，不得發送到 L3 雲端/Cloud LLM"""
        ext.simulate_edits([("main.py", 10)], content="password = 'secret123'")
        event = ext.last_event()
        assert event.payload["content_raw"] == "password = 'secret123'"
        # 驗證雲端同步管線會阻擋此欄位上傳 (由 M6.2 測試覆蓋)

class TestSocketResilience:
    def test_buffer_events_on_disconnect(self, ext):
        """驗收條件 6: Socket 斷開時本地 buffer 暫存"""
        ext.disconnect_socket()
        ext.simulate_edits([("a.py", 5)])
        assert ext.buffer_count == 1
        ext.reconnect_socket()
        assert ext.buffer_count == 0  # 已回傳
```

---

## 7. Implementation Notes

### 7.1 Shannon Entropy 計算

```typescript
// [R02: 源碼變更熵 §1.1]
function calculateChangeEntropy(editCounts: Map<string, number>): number {
    const total = Array.from(editCounts.values()).reduce((a, b) => a + b, 0);
    if (total === 0) return 0;
    let entropy = 0;
    for (const count of editCounts.values()) {
        const p = count / total;
        if (p > 0) entropy -= p * Math.log2(p);
    }
    // 正規化到 [0, 1]
    const maxEntropy = Math.log2(editCounts.size);
    return maxEntropy > 0 ? entropy / maxEntropy : 0;
}
```

### 7.2 Local Socket 通訊

- Protocol: Unix Domain Socket (Linux/macOS) 或 Named Pipe (Windows)
- Socket path: `\\.\pipe\coos_telemetry` (Windows)
- Message format: JSON Lines (每行一個 `CodeActivityEvent`)
- Reconnect: 指數退避 (1s → 2s → 4s → 8s → max 30s)

### 7.3 異常處理

| 例外情況 | 處理方式 |
| -------- | -------- |
| VS Code Extension Host crash | VS Code 自動重啟 Extension Host;M1.3.1 重新初始化計數器 |
| Local Socket 連線失敗 | 本地 buffer 暫存 (max 100 events);指數退避重連 |
| `onDidChangeTextDocument` 高頻觸發 (自動格式化) | 500ms 防抖:累積 500ms 內的所有變更為一個 `edit_burst` |

### 7.4 人機協作度量與 Agent 焦慮判定 (AI Collaboration & Churn Heuristics)

為了在 Copilot/Cursor/Cline 等 AI 輔助開發時代精確區分「人類親自動手寫」與「AI 自動生成/貼上」，M1.3.1 採用啟發式（Heuristic）判定演算法：

```typescript
// 區分人類輸入與 AI 區塊生成
interface EditChunk {
    insertedChars: number;
    deletedChars: number;
    timeDeltaMs: number;
}

function analyzeCollaboration(chunk: EditChunk): "HUMAN_TYPING" | "AI_GENERATION" | "BULK_DELETE" {
    // 若單一事件瞬間寫入大量字元（例如大於 30 字），且時間差小於 50ms，判定為 AI 生成或大塊貼上
    if (chunk.insertedChars > 30 && chunk.timeDeltaMs < 50) {
        return "AI_GENERATION";
    }
    // 人類逐字輸入通常 insertedChars 為 1-2 字且間距分佈於 50ms - 800ms
    if (chunk.insertedChars > 0 && chunk.insertedChars <= 5) {
        return "HUMAN_TYPING";
    }
    if (chunk.deletedChars > 10 && chunk.insertedChars === 0) {
        return "BULK_DELETE";
    }
    return "HUMAN_TYPING"; // 預設歸類
}

// Agent 焦慮死循環指標 (Churn Index)：計算 5 分鐘內「反覆大量刪除後又大量寫入」的比例
// 若 Churn Index 接近 1.0，代表使用者正陷入與 AI Agent 的 Bug 死循環（不斷生成、編譯失敗、刪除、再生成）
function calculateChurnIndex(events: EditChunk[]): number {
    let churnScore = 0;
    let totalChange = 0;
    for (let i = 1; i < events.length; i++) {
        const prev = events[i-1];
        const curr = events[i];
        totalChange += curr.insertedChars + curr.deletedChars;
        
        // 如果前一個事件是大量刪除，下一個事件是 AI 大量生成，此為 Churn 特徵
        if (prev.deletedChars > 50 && curr.insertedChars > 50 && curr.timeDeltaMs < 1000) {
            churnScore += (prev.deletedChars + curr.insertedChars);
        }
    }
    return totalChange > 0 ? churnScore / totalChange : 0;
}
```

---

## 8. Anti-patterns (反模式)

- ❌ **不要將原始程式碼明文 (L1) 傳輸至外部雲端或 Cloud LLM** — 僅限於發送給本地 backend 和本地 LLM 處理，絕不上傳 L3 雲端。
- ❌ **不要記錄含有使用者家目錄或系統敏感結構的絕對檔案路徑** — 僅允許記錄相對於工作區的相對路徑 (如 `src/main.rs`),且此相對路徑僅存於本地 L1 儲存,絕不上傳 L3 雲端。
- ❌ **不要在 Extension 內做推論** — 所有推論由 M2.2/M4.8 在後端完成。Extension 只是感測器。
- ❌ **不要阻塞 VS Code 主線程** — 所有 Socket 通訊必須異步,entropy 計算在 worker 中執行。
- ❌ **不要將 AI 生成的程式碼大塊寫入與人類手工敲擊混淆** — 應透過啟發式算法（如時間差與變更大小）區分以度量真實人機協作比率，否則會污染使用者認知負荷的推論。

---

## 9. Open Questions

- [x] ~~**Q1: entropy 計算的時間視窗?**~~ → 採用 **5 分鐘滑動視窗,每 30 秒更新一次**。這能平滑反應使用者的編輯模式轉換,並提供足夠即時的信號給 M1.2 斷點引擎。
- [x] ~~**Q2: 是否追蹤 Terminal panel 的活動?**~~ → **否**。VS Code 內建 Terminal 的活動由 **M1.1 (OS 遙測層)** 的全域鍵盤滑鼠計數與前景視窗 content extraction 來捕獲,M1.3.1 保持輕量化,專注於代碼編輯區。
- [x] ~~**Q3: Extension 是否需要發布到 VS Code Marketplace?**~~ → MVP 階段僅作為 **`.vsix` 本地安裝包**,打包在 coOS 安裝程式中,由 Tauri 在啟動時自動於背景下指令安裝。未來推廣時再考量上架。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責
- [x] §2 至少 1 個 `Rxx` 引用 (R02 §1.1, R02 §1.2)
- [x] §3 Schema 用 TypeScript/Pydantic 定義
- [x] §4 依賴是真實模組編號
- [x] §5 已 grep `05_integration_risk_audit.md`
- [x] §6 測試先於程式碼,覆蓋 6 個驗收條件
- [x] §8 至少 4 條反模式
- [x] §9 至少 3 個開放問題
