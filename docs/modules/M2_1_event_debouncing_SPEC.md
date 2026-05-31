# M2.1 — 事件防抖與排隊引擎

**標籤**: `[MVP]`
**版本**: `1.1`
**最後更新**: 2026-06-01

## 1. Purpose (目的)

攔截前端感知層與系統遙測層（M1.1 / M1.3）產生的高頻原始事件（如游標移動、鍵擊計數、視窗切換、瀏覽停留），在本地端進行防抖（Debounce）與排隊打包（Queueing & Batching），以 30~60 秒為週期發送批次數據。
此設計旨在：
1. 降低 Tauri IPC 通道與 FastAPI 後端的通訊負載。
2. 避免高頻請求頻繁喚醒本地/邊緣推論模型（M2.2），優化 CPU 與記憶體效能。
3. 確保離線狀態下遙測數據不丟失。

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §三.1 警報疲勞 / 認知負荷 | 藉由去抖降頻避免過度喚醒模型與推播，間接防範系統遲滯所產生的認知負荷 |
| R08 | §二 Defer-to-Breakpoint | 動態 Debounce 窗口設計靈感——不同角色對「斷點」的感知頻率差異，FAMILY 角色需 15s 快速響應，CSIE 角色需 60s 深度保護 |
| R02 | §動態上下文工程 REMT | 角色切換（`ROLE_SWITCHED`）時必須強制 Flush，防止不同角色上下文污染 IntentVector |

> 註: 本模組屬邊緣端效能優化基礎設施。R08 §三.1 為主引用，說明去抖機制如何間接防範認知負荷。

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M1.1/M1.3 遙測事件 | `RawTelemetryEvent` (見 §7.2) | `{"event_type": "keystroke", "module": "M1.3.1", "timestamp": "2026-05-31T14:20:00.123Z", "data": {"key": "Ctrl", "file_entropy": 0.15}}` |
| 系統狀態 (開關/關機) | Tauri Lifecycle Event | `TauriCloseRequest` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M2.2 推論管線 / M0.4 日誌 | `EventBatch` (見 §7.2) | `{"batch_id": "b_123", "events": [...], "size": 42}` |
| 本地臨時儲存 (溢出時) | SQLite `temp_event_queue` | 儲存在本地 SQLite 的暫存行，供重試 |

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.2** (Tauri IPC): 依賴 Rust 側的 IPC 通訊機制。
- **M1.1/M1.3** (感知層): 提供高頻率的原始數據流。

### 下游 (誰依賴我)

- **M2.2** (Gemma 邊緣推論): 接收打包好的批次事件進行意圖分析。
- **M0.4** (結構化日誌): 批次事件同時寫入本地 SQLite 的 `raw_tracking_logs`。

## 5. Known Risks (整合風險)

### RISK-M2.1-A — 當機/強制關閉導致佇列事件丟失

緩解策略：

1. 攔截 Tauri 關閉事件（Close Request），執行 Graceful Flush，將佇列殘餘事件寫入 SQLite。
2. 佇列數量超過 1000 條時，自動溢出備份至本地臨時 SQLite 檔案。

### RISK-M2.1-B — 突發高頻事件阻塞 Rust 遙測執行緒

緩解策略：採用 Rust `tokio::sync::mpsc` 非同步通道，發送端為非阻塞式 `try_send`，若佇列滿則直接拋棄低優先級事件。

### RISK-M2.1-C — 角色切換前未 Flush 導致跨角色批次污染

描述：`ROLE_SWITCHED` 事件觸發後，若 buffer 未清空，不同角色的事件將混入同一 `EventBatch`，污染 M2.2 的意圖推論上下文。

緩解策略：`[R02: REMT §動態上下文工程]` 角色切換信號觸發後，排隊引擎必須在切換完成前執行同步 Flush，強制清空目前 buffer，再以新角色設定（Debounce 窗口 + 優先級）啟動新批次。

## 6. Acceptance Criteria (驗收標準)

實作完成的定義。**先寫測試,後寫程式碼**。

```rust
// src-tauri/src/m2_1/tests.rs

#[cfg(test)]
mod tests {
    use super::*;
    use std::time::Duration;
    use tokio::time::sleep;

    #[tokio::test]
    async fn test_event_debouncing_and_batching() {
        /* 驗收條件 1: 30 秒內的高頻事件必須被打包為單一批次 */
        let (tx, rx) = tokio::sync::mpsc::channel(100);
        let debouncer = EventDebouncer::new(tx, Duration::from_millis(100), 50);
        
        // 模擬短時間內發送 10 個事件
        for i in 0..10 {
            debouncer.push(RawEvent::new("keystroke", format!("key_{}", i))).await;
        }

        // 等待防抖時間過期
        sleep(Duration::from_millis(150)).await;
        
        let batch = rx.try_recv().expect("應收到批次數據");
        assert_eq!(batch.events.len(), 10);
        assert_eq!(batch.events[0].event_type, "keystroke");
    }

    #[tokio::test]
    async fn test_queue_overflow_limit() {
        /* 驗收條件 2: 當事件數達到設定上限 (例如 50)，應立即觸發 Flush，不等待計時器 */
        let (tx, mut rx) = tokio::sync::mpsc::channel(100);
        let debouncer = EventDebouncer::new(tx, Duration::from_secs(10), 5); // 上限 5 個

        for i in 0..5 {
            debouncer.push(RawEvent::new("mouse_move", format!("pos_{}", i))).await;
        }

        // 雖然定時器是 10 秒，但因為達到上限 5，應該立刻收到
        let batch = rx.recv().await.expect("應立即觸發 Flush");
        assert_eq!(batch.events.len(), 5);
    }

    #[tokio::test]
    async fn test_graceful_flush_on_shutdown() {
        /* 驗收條件 3: 當觸發 shutdown 時，即使時間未到且未達上限，也必須強制 Flush */
        let (tx, mut rx) = tokio::sync::mpsc::channel(100);
        let debouncer = EventDebouncer::new(tx, Duration::from_secs(60), 100);

        debouncer.push(RawEvent::new("focus_change", "vscode")).await;
        
        // 執行關閉
        debouncer.shutdown_gracefully().await;

        let batch = rx.recv().await.expect("關閉時應強制 Flush");
        assert_eq!(batch.events.len(), 1);
        assert_eq!(batch.events[0].data, "vscode");
    }

    #[tokio::test]
    async fn test_role_switch_forces_flush() {
        /* 驗收條件 4 (RISK-M2.1-C): ROLE_SWITCHED 信號必須觸發同步 Flush，
           且新批次不得包含切換前的事件 */
        let (tx, mut rx) = tokio::sync::mpsc::channel(100);
        let mut debouncer = EventDebouncer::new(tx, Duration::from_secs(60), 100);

        // 以 CSIE 角色推入事件
        debouncer.push(RawEvent::new("keystroke", "csie_event")).await;

        // 觸發角色切換
        debouncer.on_role_switched("FAMILY", Duration::from_secs(15)).await;

        // 應立即收到 CSIE 角色的舊批次
        let old_batch = rx.recv().await.expect("角色切換應強制 Flush 舊批次");
        assert_eq!(old_batch.events.len(), 1);
        assert_eq!(old_batch.events[0].data, "csie_event");

        // 推入 FAMILY 角色事件，確認新批次乾淨
        debouncer.push(RawEvent::new("focus_change", "family_event")).await;
        debouncer.shutdown_gracefully().await;
        let new_batch = rx.recv().await.expect("應收到 FAMILY 批次");
        assert_eq!(new_batch.events.len(), 1);
        assert_eq!(new_batch.events[0].data, "family_event");
    }

    #[tokio::test]
    async fn test_offline_exponential_backoff() {
        /* 驗收條件 5: FastAPI 不可達時，批次落地 SQLite 並以指數退避排程重試 */
        let (tx, _rx) = tokio::sync::mpsc::channel(100);
        let debouncer = EventDebouncer::new(tx, Duration::from_millis(50), 5);
        debouncer.push(RawEvent::new("keystroke", "k1")).await;
        sleep(Duration::from_millis(100)).await;

        // 模擬 FastAPI 不可達：送出批次應失敗並寫入 SQLite offline buffer
        let offline_count = debouncer.offline_buffer_len().await;
        // 離線時 buffer 應 > 0，且重試排程已啟動（首次 5s）
        assert!(offline_count > 0, "應有批次寫入離線 buffer");
        let retry_delay = debouncer.next_retry_delay().await;
        assert_eq!(retry_delay.as_secs(), 5, "首次重試應為 5 秒");
    }
}
```

## 7. Implementation Notes

### 7.1 演算法選擇

採用 **Token Bucket / Slide Window Batching** 變體：
- 設置兩個觸發 Flush 門檻：
  - **時間門檻（Temporal Threshold）**：自批次內第一個事件寫入起算，達到 30 秒（預設）時觸發。
  - **數量門檻（Capacity Threshold）**：當未決事件數量達到 1000 條時，立刻觸發 Flush。
- 對於超高頻的滑鼠軌跡事件，在進入 Queue 之前先進行預過濾，僅在座標偏移大於特定像素（如 50px）或停頓超過 500ms 時才保留事件。

### 7.2 資料結構

```rust
// src-tauri/src/m2_1/schema.rs

use serde::{Serialize, Deserialize};
use chrono::{DateTime, Utc};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawTelemetryEvent {
    pub id: String,
    pub event_type: String, // "keystroke", "mouse_move", "focus_change", "ast_change"
    pub module: String,     // "M1.1.2", "M1.3.1" 等
    pub timestamp: DateTime<Utc>,
    pub data: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventBatch {
    pub batch_id: String,
    pub created_at: DateTime<Utc>,
    pub events: Vec<RawTelemetryEvent>,
    pub size: usize,
}
```

### 7.3 異常處理

- **Tauri 主進程崩潰**：在啟動時檢查臨時目錄中是否存在未完成的 `temp_events.db`。若有，優先載入並發送至 M2.2。
- **FastAPI 連線中斷**：若下游 FastAPI 服務不可達，事件批次寫入本地 SQLite 的暫存區，啟動 5 秒/15 秒/60 秒指數退避（Exponential Backoff）重試機制。
- **記憶體警報（Tauri OOM 防止）**：當排隊佇列佔用記憶體估計超過 20MB 時，強制執行 Flush 落盤，清空記憶體緩衝。

## 8. Anti-patterns (反模式)

- ❌ **不可繞過排隊引擎直接發送高頻事件至 FastAPI。**
  理由：高頻的 HTTP/IPC 呼叫會導致 Python FastAPI Sidecar CPU 飆升至 100%，並拖慢對話回應（破壞 R05 治療同盟）。
- ❌ **不可使用無界記憶體佇列（Unbounded Queue）。**
  理由：當 FastAPI 離線且使用者持續工作時，無界佇列會導致 Tauri RAM 迅速耗盡。
- ❌ **不可在遙測擷取執行緒（Telemetry Capture Thread）中直接進行 IO 寫入或網路請求。**
  理由：IO 阻塞會導致 OS 遙測漏勾或造成使用者鍵盤輸入卡頓（Resumption Lag）。
- ❌ **不可在角色切換完成後才執行 Flush（先換角色後清 buffer）。**
  理由：觸發 RISK-M2.1-C，切換前的舊角色事件會混入新角色的首個 `EventBatch`，導致 M2.2 以新角色設定推論出錯誤的意圖上下文，污染整條 IntentVector → M5.1 圖譜鏈。Flush 必須在角色設定切換前完成（先 Flush，後切換）。

## 9. Open Questions (已決議)

- [x] **滑鼠軌跡（Mouse Telemetry）的實用性**
  * **決議**：在 M1.1 (OS 遙測層) 完全停用 `mouse_move` 物理座標軌跡上報。僅保留「滑鼠點擊 (mouse_click)」與「特定區域停留超過 500ms (hover)」，並藉由 OS UIAutomation API 將其轉譯為語意化事件（例如點擊了哪個 button / 關注了哪個 tab），以大幅降低 M2.1 頻寬與記憶體壓力。
- [x] **Debounce 窗口大小是否應與當前 Role 綁定**
  * **決議**：支援動態窗口。不同生活角色具備不同的 Debounce 窗口（例如專注角色如 CSIE 設為 60s 以保護專注；互動/社交角色如 FAMILY 設為 15s 以求快速反應）。在角色切換（`ROLE_SWITCHED`）的瞬間，排隊引擎必須**立即執行強制 Flush**（Graceful Flush）將當前暫存數據發送，防止不同角色的數據流交叉污染，隨後再套用新角色的窗口設定。
