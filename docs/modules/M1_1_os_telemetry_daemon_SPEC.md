# M1.1 — OS 級別遙測守護行程 (Rust Native)

**標籤**: `[MVP]`
**版本**: `1.2`
**最後更新**: 2026-06-02

---

## 子模組 SPEC 決策說明

M1.1 包含四個子模組 (M1.1.1~M1.1.4),**合併為單一 SPEC** 的理由:

1. **同一 Rust 行程**:四個子模組共存於同一 `services/m1_1_telemetry_daemon/` crate,共享行程生命週期。
2. **相同輸出管道**:皆透過 M0.4 寫入 `raw_tracking_logs`,輸出 schema 相同。
3. **隱私約束橫切**:M1.1.4 的硬體禁用約束是對整個行程而言的守門員,若拆開則四個 SPEC 都要重複相同的 Anti-pattern 區塊。
4. **驗收標準耦合**:「30 分鐘活躍時段正確分桶」需要 M1.1.2 + M1.1.3 同時工作才能驗收,拆開會使測試孤兒化。

拆分時機:若未來 M1.1.1 須支援 macOS / Linux 多平台,屆時可獨立 `M1_1_1_uiautomation_SPEC.md`。

---

## 1. Purpose (目的)

在 OS 層以 Rust Native 守護行程收集焦點/鍵鼠/視窗事件與**可選的應用程式內文**,經結構化處理後寫入 `raw_tracking_logs`,作為系統所有 AI 推論的感知神經末梢。

> 一句話:「**原始信號採集 + Opt-in 內文讀取 + Local LLM 摘要 = 本地安全的行為與脈絡特徵流**」。
>
> v1.1 變更:使用者可主動開啟「內文採集模式」(全部或指定軟體),允許讀取視窗標題與焦點區域內文,由 Local LLM (M2.2) 產出摘要。所有原始內文僅存本地 SQLite (L1),**絕不上雲**。

---

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R02 | §計算心理語言學 §1 | WPM 與停留時間作為認知狀態的輸入特徵,供 M4.8 隱性狀態推論使用 |
| R02 | §時間動力學 §1.2 | 提交間距爆發性特徵的前置資料:焦點視窗切換頻率 + 活躍時長 |
| R06 | §數位表型 §2.1 | 鍵鼠行為模式作為數位表型感測器,為多維度開發者輪廓提供原始訊號 |
| R06 | §第七章 差分隱私 | 去識別化設計預留差分隱私擴充介面 (M2.4 未來使用) |
| R07 | §3 IDE 脈絡與螢幕焦點擷取 | Opt-in 內文採集的技術基礎:UIAutomation 焦點控制項純文字讀取 |
| R10 | §認知負荷消解 | 內文摘要供 AI 專家自然套問,降低使用者手動記錄負擔 |

---

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| Windows UIAutomation API | `HWND`, `IUIAutomation2` COM 介面 | `{ window_title: "main.py - VSCode", process: "Code.exe" }` |
| Windows Raw Input API | 鍵盤/滑鼠底層事件 | `{ key_count: 42, mouse_distance_px: 1200, interval_ms: 500 }` |
| Windows `GetForegroundWindow` 輪詢 | HWND + `GetWindowThreadProcessId` | `{ hwnd: 0x1A2B3C, pid: 12345 }` |
| Tauri App 生命週期事件 | M0.2 `AppHandle` 訊號 | `"app_started"`, `"app_will_close"` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| M0.4 → `raw_tracking_logs` (L1) | 見 §7.2 `TelemetryEvent` | `{ module: "M1.1.2", action: "keystroke_burst", payload: {...} }` |
| M0.4 → `raw_tracking_logs` (L1, Opt-in) | `ContentCapturePayload` | `{ window_title: "報告.docx - Word", content_summary: "正在編輯實驗方法段落", privacy_tier: "T1_OPTIN" }` ※ `content_raw` (原始明文) 不寫入 `raw_tracking_logs.payload`,另以獨立欄位 `content_raw_ref` 存於本地 L1 附屬表 |
| Tauri 前端事件 (M0.2 channel) | `m1_1_focus_changed` | `{ app: "VSCode", duration_s: 1823, bucket: "coding" }` |
| M1.2 訂閱的 `focus_session_ended` | `FocusSessionEvent` | `{ duration_s: 1823, app_bucket: "coding", wpm_avg: 48, activity_state: "DEEP_FOCUS" }` |
| M0.4 → `raw_tracking_logs` (L1) | `SecondaryWindowSnapshot` | `{ windows: [{app: "Chrome", bucket: "reading", visible_s: 300}] }` |
| M1.2 訂閱的 `activity_state_changed` | `ActivityStateEvent` | `{ prev_state: "ACTIVE", new_state: "DEEP_FOCUS", confidence: 0.85 }` |

---

## 4. Dependencies

### 上游 (我依賴誰)

- **M0.2** (Tauri IPC): 行程啟動/關閉由 M0.2.1 Rust `Command` 管理;需透過 M0.2.2 WebSocket/SSE 通道回報事件至前端
- **M0.4** (結構化日誌): 寫入 `raw_tracking_logs` 的管線;M1.1 必須呼叫 M0.4 的寫入介面,不可繞過直接寫入 SQLite
- **M6.1** (SQLite schemas): `raw_tracking_logs` 資料表定義來自此模組;M1.1 不擁有 schema,僅是生產者

### 下游 (誰依賴我)

- **M1.2** (斷點偵測): 訂閱 `focus_session_ended` 事件,作為斷點偵測的主要輸入訊號
- **M4.8** (隱性狀態推論): 從 `raw_tracking_logs` 讀取鍵鼠/焦點事件推論認知狀態 `[R02 §1, R06 §2.1]`
- **M2.2** (Gemma 邊緣推論): 批次讀取 `raw_tracking_logs` 進行意圖向量壓縮;**Opt-in 模式下**接收 `content_raw` 產出 `content_summary`
- **M4.4** (深夜草稿觸發): 讀取焦點時段資料拼裝工作時長;可引用 `content_summary` 豐富草稿脈絡（須經 M2.3 Eguard 過濾後方可進入草稿）

---

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| (無直接 RISK-xx) | M1.1 高頻寫入 + SQLite WAL 模式並發 → `database is locked` | M0.4 寫入管線使用 `arq` 非同步佇列批次寫入,M1.1 只發事件到佇列不直接觸碰 SQLite |
| (無直接 RISK-xx) | UIAutomation COM 呼叫在某些視窗 (管理員權限) 返回 `AccessDenied` | 僅捕獲可讀視窗;AccessDenied 靜默跳過,不拋 panic,記錄 `level: "WARN"` |
| (無直接 RISK-xx) | Windows Raw Input 在無焦點視窗時仍持續累積事件 → 假陽性 WPM 飆升 | 只在 `is_foreground_active = true` 時累積鍵鼠計數 |
| (無直接 RISK-xx) | 守護行程 crash → M1.2 停止收到訊號 → 誤判「使用者離開」 | M0.2.1 設置 3 秒 watchdog 重啟;M1.2 設置 10 秒無訊號 timeout 保護 |
| **RISK-15** | Opt-in 內文摘要 (`content_summary`) 經 M4.4 草稿引用後進入 M6.2 雲端同步 → 側通道洩漏 | (1) `content_raw` 與 `content_summary` 嚴格鎖定 L1,標記 `privacy_tier = "T1_OPTIN"`;(2) M4.4 草稿引用 `content_summary` 前必須經 M2.3 Eguard 泛化,絕不原文複製;(3) M6.2 雲端同步管線設置 hard block:payload 含 `content_raw` 或 `content_summary` 欄位時拒絕同步。完整緩解見 `05_integration_risk_audit.md RISK-15` |

---

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m1_1/test_telemetry_daemon.py

import pytest
import time
from unittest.mock import patch, MagicMock
from services.m1_1_telemetry_daemon import TelemetryDaemon, TelemetryEvent


class TestFocusSessionBucketing:
    def test_30min_active_session_correctly_bucketed(self, daemon, mock_db):
        """驗收條件 1: 30 分鐘活躍時段正確分桶記錄"""
        daemon.simulate_focus("Code.exe", duration_s=1800)
        events = mock_db.query_by_module("M1.1.3")
        session = next(e for e in events if e.action == "focus_session_ended")
        assert session.payload["duration_s"] >= 1800
        assert session.payload["app_bucket"] == "coding"
        assert session.payload["wpm_avg"] > 0

    def test_short_focus_under_30s_not_emitted(self, daemon, mock_db):
        """驗收條件 2: 30 秒以下的焦點切換不記為有效時段"""
        daemon.simulate_focus("Code.exe", duration_s=15)
        events = mock_db.query_by_module("M1.1.3")
        assert not any(e.action == "focus_session_ended" for e in events)


class TestPIINotPersistedRaw:
    def test_no_raw_keystrokes_in_payload(self, daemon, mock_db):
        """驗收條件 3: payload 中不存在原始按鍵序列 (PII 不落盤)"""
        daemon.simulate_keystrokes("Hello, password123")
        events = mock_db.query_by_module("M1.1.2")
        for event in events:
            payload_str = str(event.payload)
            assert "password" not in payload_str.lower()
            assert "Hello" not in payload_str
            assert "123" not in payload_str

    def test_window_title_truncated_not_raw(self, daemon, mock_db):
        """驗收條件 4: window_title 僅保留 app 名稱,不存 URL 或檔案內容片段"""
        daemon.simulate_focus("Chrome - gmail.com/inbox - 14 unread", duration_s=120)
        events = mock_db.query_by_module("M1.1.1")
        for event in events:
            assert "gmail.com" not in str(event.payload)
            assert "14 unread" not in str(event.payload)

    def test_no_plaintext_content_in_raw_tracking_logs_when_optin_off(self, mock_db):
        """驗收條件 5: CaptureMode::Off (預設) 時 payload 不含任何明文內容欄位"""
        # 前提: daemon 以 CaptureMode::Off 運行 (預設值)
        all_events = mock_db.query_all()
        for event in all_events:
            assert event.payload.get("raw_text") is None
            assert event.payload.get("clipboard") is None
            assert event.payload.get("content_raw") is None
            assert event.payload.get("window_title") is None  # Off 模式下不留視窗標題


class TestHardwarePrivacyConstraints:
    def test_camera_never_accessed(self, daemon):
        """驗收條件 6: 行程生命週期內不存取攝影機裝置"""
        with patch("win32api.OpenProcess") as mock_open:
            daemon.start()
            time.sleep(0.1)
            camera_handles = [
                c for c in mock_open.call_args_list
                if "camera" in str(c).lower() or "video" in str(c).lower()
            ]
            assert len(camera_handles) == 0

    def test_microphone_never_accessed(self, daemon):
        """驗收條件 7: 行程生命週期內不存取麥克風"""
        with patch("win32api.waveInGetNumDevs", return_value=0) as mock_wave:
            daemon.start()
            assert mock_wave.call_count == 0


class TestWPMCalculation:
    def test_wpm_calculated_over_60s_window(self, daemon):
        """驗收條件 8: WPM 基於 60 秒滑動視窗計算"""
        daemon.simulate_keystrokes_over_time(key_count=300, duration_s=60)
        wpm = daemon.get_current_wpm()
        assert 55 <= wpm <= 65  # 300 keystrokes / 5 chars_per_word / 1 min

    def test_wpm_resets_on_focus_change(self, daemon):
        """驗收條件 9: 焦點切換時 WPM 滑動視窗重置"""
        daemon.simulate_keystrokes_over_time(key_count=300, duration_s=60)
        daemon.simulate_focus_change("Slack.exe")
        assert daemon.get_current_wpm() == 0


class TestDaemonResilience:
    def test_daemon_emits_heartbeat_every_30s(self, daemon, mock_db):
        """驗收條件 10: 守護行程每 30 秒發出 heartbeat,供 M0.2.1 watchdog 監控"""
        daemon.start()
        time.sleep(35)
        heartbeats = mock_db.query_by_action("daemon_heartbeat")
        assert len(heartbeats) >= 1

    def test_uiautomation_access_denied_does_not_crash(self, daemon):
        """驗收條件 11: UIAutomation AccessDenied 靜默處理,不拋 panic"""
        with patch("win32gui.GetWindowText", side_effect=PermissionError("AccessDenied")):
            try:
                daemon.poll_foreground_window()
            except Exception:
                pytest.fail("UIAutomation AccessDenied should be silently skipped")
```

---

## 7. Implementation Notes

### 7.1 子模組職責邊界

| 子模組 | Rust 模組路徑 | 核心職責 |
| ------ | ------------- | -------- |
| M1.1.1 | `src/m1_1_1_uiautomation.rs` | `IUIAutomation2` COM 橋接;抓取前景視窗標題與 process name;**Opt-in 模式下**讀取焦點控制項純文字內文 (`UIA_ValuePattern` / `UIA_TextPattern`),送 M2.2 產出 `content_summary` |
| M1.1.2 | `src/m1_1_2_input_debouncer.rs` | Windows Raw Input API hook;計算 60s 滑動視窗 WPM;即時去識別化 (字符計數,非明文) |
| M1.1.3 | `src/m1_1_3_focus_tracker.rs` | 前景視窗變換事件;累積焦點時長;30 分鐘時段分桶;`focus_session_ended` 事件派發;**多螢幕次要視窗掃描** (每 30 秒 `EnumWindows`,記錄可見視窗的 process + app_bucket + 可見時長);**行為狀態分類器 (ActivityStateClassifier)**:根據多信號融合判定使用者當前行為狀態 (八態分類,見 §7.5) |
| M1.1.4 | `src/m1_1_4_privacy_guard.rs` | 行程啟動時驗證攝影機/麥克風/GPS handle 未開啟;提供 `assert_no_hw_capture()` |

### 7.2 TelemetryEvent Schema (Pydantic 等效 — Rust `serde`)

```rust
// services/m1_1_telemetry_daemon/src/models.rs

#[derive(Serialize, Deserialize, Debug)]
pub struct TelemetryEvent {
    pub id: String,          // UUID v4
    pub timestamp: String,   // ISO 8601 UTC
    pub module: String,      // "M1.1.1" | "M1.1.2" | "M1.1.3" | "M1.1.4"
    pub action: TelemetryAction,
    pub level: LogLevel,
    pub payload: serde_json::Value,  // 結構化摘要,無明文
    pub correlation_id: Option<String>,
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(rename_all = "snake_case")]
pub enum TelemetryAction {
    FocusSessionEnded,
    KeystrokeBurst,
    MouseActivitySummary,
    WindowChanged,
    DaemonHeartbeat,
    PrivacyAssertionPassed,
    PrivacyAssertionFailed,
    ActivityStateChanged,  // M1.1.3 八態分類器狀態轉換時發出
    SecondaryWindowSnapshot,  // M1.1.3 每 30 秒次要視窗掃描結果
}

// M1.1.3 focus_session_ended 的 payload
#[derive(Serialize, Deserialize, Debug)]
pub struct FocusSessionPayload {
    pub app_name: String,           // "Code" (process name, 非視窗標題)
    pub app_bucket: AppBucket,      // coding | writing | reading | communication | idle
    pub duration_s: u64,
    pub wpm_avg: f32,               // 0 if not typing session
    pub mouse_clicks: u32,
    pub mouse_distance_norm: f32,   // 正規化到 [0,1],不含絕對像素位置
    pub activity_state: ActivityState, // v1.2 新增:行為狀態分類器結果
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(rename_all = "snake_case")]
pub enum AppBucket {
    Coding,
    Writing,
    Reading,
    Communication,
    Productivity,
    Idle,
    Unknown,
}

// v1.2 新增:行為狀態八態分類器 [R06: 數位表型 §2.1]
#[derive(Serialize, Deserialize, Debug, Clone, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ActivityState {
    /// 單一工作類 app 持續 > 10 min + WPM 穩定 + 無娛樂類 app 切換
    DeepFocus,
    /// 有鍵鼠活動,正常使用電腦
    Active,
    /// 前景為媒體播放器/全螢幕瀏覽器 + 無鍵鼠活動 > 2 min (長影片觀賞)
    PassiveConsumption,
    /// 高頻捲動(>30/min) + 頁面停留時間短(<15s) + 社交/娛樂/新聞類 app + 持續 ≥ 5 min
    DoomScrolling,
    /// 5 min 內在 ≥ 4 個不同 app 間切換,每個停留 < 60s
    ContextSwitching,
    /// 瀏覽器/PDF 閱讀器為主 + 低 WPM + 頁面停留 > 2 min + 非娛樂類
    ResearchReading,
    /// 視訊/語音通話 app (Zoom/Teams/Discord) 為前景 + 持續 > 5 min
    MeetingCall,
    /// 連續無活動 > 5 min
    Idle,
}
```

### 7.3 去識別化與內文採集規則 (M1.1.1)

```rust
// [R06: 數位表型 §2.1 + R07 §3] 根據 CaptureMode 決定保留程度

/// Opt-in 同意機制 (從 M6.1 `user_consents` 表讀取, consent_type = 'content_capture_all' 或 'content_capture_selected')
pub struct CaptureConsent {
    pub mode: CaptureMode,
    pub allowed_processes: Vec<String>,  // ["Code.exe", "WINWORD.EXE", "Notion.exe"]
    pub updated_at: String,
}

pub enum CaptureMode {
    Off,           // v1.0 行為:僅 process name + 統計值
    AllApps,       // 全部軟體開啟內文採集
    SelectedApps,  // 僅白名單軟體
}

fn process_window(raw_title: &str, process_name: &str, consent: &CaptureConsent) -> WindowCapture {
    let bucket = classify_process(process_name);

    match consent.mode {
        CaptureMode::Off => {
            // v1.0 行為:視窗標題完全丟棄
            WindowCapture {
                app_name: process_name.to_string(),
                app_bucket: bucket,
                window_title: None,
                content_raw: None,
                content_summary: None,
            }
        }
        CaptureMode::AllApps => {
            // 全部軟體:標題落盤 + 分層內文截取
            let content = read_focused_content_layered(process_name);
            WindowCapture {
                app_name: process_name.to_string(),
                app_bucket: bucket,
                window_title: Some(raw_title.to_string()),
                content_raw: content,
                content_summary: None,  // M2.2 後續填入;離線時走 §7.7 fallback
            }
        }
        CaptureMode::SelectedApps => {
            if consent.allowed_processes.contains(&process_name.to_string()) {
                let content = read_focused_content_layered(process_name);
                WindowCapture {
                    app_name: process_name.to_string(),
                    app_bucket: bucket,
                    window_title: Some(raw_title.to_string()),
                    content_raw: content,
                    content_summary: None,
                }
            } else {
                // 不在白名單:同 Off 模式
                WindowCapture {
                    app_name: process_name.to_string(),
                    app_bucket: bucket,
                    window_title: None,
                    content_raw: None,
                    content_summary: None,
                }
            }
        }
    }
}

/// 多螢幕次要視窗掃描 (每 30 秒)
#[derive(Serialize, Deserialize, Debug)]
pub struct SecondaryWindowSnapshot {
    pub windows: Vec<SecondaryWindowEntry>,
    pub scanned_at: String,
}

#[derive(Serialize, Deserialize, Debug)]
pub struct SecondaryWindowEntry {
    pub app_name: String,
    pub app_bucket: AppBucket,
    pub visible_since: String,     // ISO 8601
    pub monitor_index: u32,        // 0-based 螢幕索引
}
```

### 7.4 WPM 滑動視窗演算法

```rust
// [R02: 計算心理語言學 §1] WPM = key_count / avg_chars_per_word / elapsed_minutes
// 使用 60 秒固定視窗,焦點切換時重置
struct WpmCalculator {
    window: VecDeque<(Instant, u32)>,  // (timestamp, key_count_delta)
    window_size: Duration,             // 60s
}

impl WpmCalculator {
    const AVG_CHARS_PER_WORD: f32 = 5.0;

    fn push(&mut self, key_count: u32) {
        let now = Instant::now();
        self.window.push_back((now, key_count));
        // 清除視窗外的舊資料
        while self.window.front().map_or(false, |(t, _)| now - *t > self.window_size) {
            self.window.pop_front();
        }
    }

    fn current_wpm(&self) -> f32 {
        let total_keys: u32 = self.window.iter().map(|(_, k)| k).sum();
        total_keys as f32 / Self::AVG_CHARS_PER_WORD
        // elapsed 固定為 1 分鐘視窗 → 直接等於 WPM
    }

    fn reset(&mut self) {
        self.window.clear();
    }
}
```

### 7.5 行為狀態分類器 (ActivityStateClassifier)

```rust
// v1.2 新增 [R06: 數位表型 §2.1]
// 根據多信號融合每 30 秒重新分類使用者行為狀態

/// 分類所需的輸入信號
struct ClassifierInput {
    current_app: String,
    app_bucket: AppBucket,
    focus_duration_s: u64,         // 當前 app 持續焦點時長
    wpm_avg: f32,                  // 60s 滑動視窗 WPM
    scroll_events_per_min: u32,    // 每分鐘捲動次數
    page_stay_avg_s: f32,          // 平均頁面停留時間
    app_switch_count_5min: u32,    // 過去 5 分鐘 app 切換次數
    is_fullscreen: bool,           // 前景 app 是否全螢幕
    is_media_app: bool,            // 前景是否為媒體播放器
    is_meeting_app: bool,          // 前景是否為視訊/通話 app
    is_entertainment_app: bool,    // 前景是否為社交/娛樂/新聞類
    idle_duration_s: u64,          // 無鍵鼠活動持續時長
}

fn classify_activity_state(input: &ClassifierInput) -> ActivityState {
    // 優先序:越嚴格的狀態越先判定
    
    // 1. IDLE:最明確的信號
    if input.idle_duration_s > 300 {
        return ActivityState::Idle;
    }
    
    // 2. MEETING_CALL:視訊/通話 app 前景 > 5 min
    if input.is_meeting_app && input.focus_duration_s > 300 {
        return ActivityState::MeetingCall;
    }
    
    // 3. DOOM_SCROLLING:高頻捲動 + 停留短 + 娛樂類 + 持續 ≥ 5 min
    if input.scroll_events_per_min > 30
        && input.page_stay_avg_s < 15.0
        && input.is_entertainment_app
        && input.focus_duration_s >= 300
    {
        return ActivityState::DoomScrolling;
    }
    
    // 4. PASSIVE_CONSUMPTION:全螢幕媒體 + 無鍵鼠 > 2 min
    if (input.is_media_app || (input.is_fullscreen && input.app_bucket == AppBucket::Reading))
        && input.idle_duration_s > 120
    {
        return ActivityState::PassiveConsumption;
    }
    
    // 5. CONTEXT_SWITCHING:5 min 內 ≥ 4 app 切換
    if input.app_switch_count_5min >= 4 {
        return ActivityState::ContextSwitching;
    }
    
    // 6. DEEP_FOCUS:單一工作 app > 10 min + WPM 穩定或持續互動
    if input.focus_duration_s > 600
        && !input.is_entertainment_app
        && matches!(input.app_bucket, AppBucket::Coding | AppBucket::Writing | AppBucket::Productivity)
    {
        return ActivityState::DeepFocus;
    }
    
    // 7. RESEARCH_READING:閱讀器 + 低 WPM + 頁面停留 > 2 min
    if matches!(input.app_bucket, AppBucket::Reading)
        && input.wpm_avg < 10.0
        && input.page_stay_avg_s > 120.0
        && !input.is_entertainment_app
    {
        return ActivityState::ResearchReading;
    }
    
    // 8. 預設:ACTIVE
    ActivityState::Active
}
```

> **活躍狀態的下游影響**：
> - `DEEP_FOCUS` → M1.2 進入 DEEP_WORK 攔截 L2 通知
> - `PASSIVE_CONSUMPTION` / `DOOM_SCROLLING` → M1.2 視為低認知負荷,允許 L2 通知
> - `CONTEXT_SWITCHING` → M4.8 推論為焦慮/分心信號 [R02 §1.2]
> - `MEETING_CALL` → M1.2 進入 DEEP_WORK (不打擾會議)
> - `RESEARCH_READING` → M1.2 視為輕度工作,L2 通知排隊
> - `IDLE` → M1.2 觸發斷點

### 7.6 異常處理

| 例外情況 | 處理方式 |
| -------- | -------- |
| `IUIAutomation2` COM 初始化失敗 | 寫入 `level: "ERROR"` log,M1.1.1 降級為「僅追蹤 process name」模式,不 panic |
| `GetForegroundWindow` 返回 NULL | 視為 `AppBucket::Idle`,靜默繼續 |
| Raw Input hook 無法安裝 (權限不足) | 寫入 `level: "WARN"` log,M1.1.2 停用,其餘子模組正常運作 |
| `raw_tracking_logs` 佇列滿 (M0.4 背壓) | 丟棄最舊的 `KeystrokeBurst` 事件 (低優先);保留 `FocusSessionEnded` 事件 (高優先) |
| UIAutomation `AccessDenied` (管理員視窗) | `level: "WARN"` 靜默跳過;不補填前一視窗資料 |
| ActivityStateClassifier 信號不足 (開機前 30 秒) | 預設為 `Active`,待信號累積後重新分類 |

### 7.7 內文分層截取策略 (v1.2 新增)

```rust
// [R07 §3] Opt-in 模式下的內文截取策略
// 上限:MAX_CONTENT_RAW_CHARS = 4000 字元

const MAX_CONTENT_RAW_CHARS: usize = 4000;

/// 分層截取策略:焦點 > 標題 > 主要區塊
fn read_focused_content_layered(process_name: &str) -> Option<String> {
    let mut result = String::new();
    let mut budget = MAX_CONTENT_RAW_CHARS;
    
    // Layer 1: 焦點控制項文字 (UIA_ValuePattern / UIA_TextPattern)
    if let Some(focus_text) = read_uia_focus_element() {
        let chunk = truncate_to_budget(&focus_text, budget);
        result.push_str("[FOCUS] ");
        result.push_str(&chunk);
        budget = budget.saturating_sub(chunk.len() + 8);
    }
    
    // Layer 2: 視窗標題列文字
    if budget > 0 {
        if let Some(title_text) = read_uia_title_bar() {
            let chunk = truncate_to_budget(&title_text, budget.min(200));
            result.push_str("\n[TITLE] ");
            result.push_str(&chunk);
            budget = budget.saturating_sub(chunk.len() + 9);
        }
    }
    
    // Layer 3: 主要內容區塊 (文件正文、編輯器可見範圍)
    if budget > 0 {
        if let Some(main_text) = read_uia_main_content() {
            let chunk = truncate_to_budget(&main_text, budget);
            result.push_str("\n[MAIN] ");
            result.push_str(&chunk);
        }
    }
    
    if result.is_empty() { None } else { Some(result) }
}
```

### 7.8 ContentSummary Fallback (v1.2 新增)

```rust
// M2.2 Gemma 離線時的 rule-based content_summary 降級產出
// 在本機直接從 content_raw 萃取摘要,不需 LLM

fn generate_content_summary_fallback(content_raw: &str, window_title: &str) -> String {
    let mut summary = String::new();
    
    // 1. 焦點區塊標題 (若有 [TITLE] 標記)
    if let Some(title_start) = content_raw.find("[TITLE] ") {
        let title_end = content_raw[title_start..]
            .find('\n')
            .unwrap_or(content_raw.len() - title_start);
        let title = &content_raw[title_start + 8..title_start + title_end];
        summary.push_str(title.trim());
        summary.push_str(" — ");
    }
    
    // 2. 焦點區塊前 200 字
    if let Some(focus_start) = content_raw.find("[FOCUS] ") {
        let focus_content = &content_raw[focus_start + 8..];
        let end = focus_content.find('\n').unwrap_or(focus_content.len());
        let truncated: String = focus_content[..end]
            .chars()
            .take(200)
            .collect();
        summary.push_str(&truncated);
    } else {
        // 無焦點標記:直接取前 200 字
        let truncated: String = content_raw.chars().take(200).collect();
        summary.push_str(&truncated);
    }
    
    summary
}
```

> **注意**:此 fallback 產出的 `content_summary` 仍標記為 `inference_mode: "rule_based_fallback"`,且同樣嚴格鎖定 L1,絕不上雲。M2.2 恢復後將批次重新產出 LLM 版本的 summary 並覆蓋。

---

## 8. Anti-patterns (反模式)

- ❌ **不要在未經使用者 Opt-in 同意時讀取內文或保留視窗標題** — `CaptureMode::Off` 是預設值,此時行為必須與 v1.0 完全一致。違反即為未授權資料收集。
- ❌ **不要讓 `content_raw` 或 `content_summary` 離開 L1 層** — 即使 Opt-in 開啟,內文相關欄位僅存本地 SQLite,絕不進入 M6.2 雲端同步。`[RISK-15 緩解]`
- ❌ **不要讓 M1.1 直接呼叫 SQLite** — 所有寫入必須經過 M0.4 寫入管線。直接寫入會繞過 WAL 批次保護,導致鎖定競爭。
- ❌ **不要在 M1.1.2 存儲原始按鍵序列** — 只允許存統計值 (key_count, wpm)。字符序列重組可還原為密碼/文字 = PII。`[架構文件 §3 L1 明文]`
- ❌ **不要在無焦點時繼續累積鍵鼠計數** — 使用者可能在其他 app 輸入密碼,後台累積造成 WPM 計算污染 + 隱私風險。
- ❌ **不要向前端廣播原始內文或鍵鼠速率** — M0.2.2 通道的事件只包含 `app_bucket + duration_s + wpm_avg`,不含原始內文或計數。`content_summary` 只透過 DB 查詢提供給後端 M4.4。
- ❌ **不要開啟任何音訊/視訊 device handle** — M1.1.4 在啟動時主動斷言這些 handle 未被佔用。若需要語音功能,由未來 M3.4.3.3 負責,有獨立的 `user_consents` 前置條件。`[RISK-11 緩解前置]`

---

## 9. Open Questions

實作前必須與使用者拍板:

- [x] ~~**Q1: Windows 管理員視窗的焦點時間是否納入計算?**~~ → 是,納入計算但 app_bucket = `Unknown`。
- [x] ~~**Q2: 多螢幕環境下「前景視窗」如何定義?**~~ → 採用「主焦點 + 次要可見視窗」方案。主焦點 = `GetForegroundWindow`;每 30 秒 `EnumWindows` 掃描所有可見視窗作為次要記錄。鍵鼠僅歸主焦點。
- [x] ~~**Q3: 行程是否以 Tauri plugin 形式嵌入,還是獨立 sidecar?**~~ → 確認 **sidecar 模式**。維持 M0.2.1 現有的 watchdog 邏輯,M1.1 守護行程作為獨立 `.exe` 由 Tauri 主行程管理。
- [x] ~~**Q4: 30 分鐘時段分桶的意義是什麼?**~~ → 活躍定義：60 秒視窗內 `key_count > 0` 或 `mouse_distance_norm > 0.1` 即為活躍；連續非活躍 5 分鐘即為時段結束。此外，從二元（活躍/閒置）升級為**八態行為狀態分類器** (§7.5 `ActivityStateClassifier`)：`DEEP_FOCUS`、`ACTIVE`、`PASSIVE_CONSUMPTION`（含長影片觀賞）、`DOOM_SCROLLING`（高頻捲動 + 停留短 + 社交/娛樂/新聞類 + ≥5 min）、`CONTEXT_SWITCHING`、`RESEARCH_READING`、`MEETING_CALL`、`IDLE`。
- [x] ~~**Q5: Opt-in 內文採集的 `content_raw` 截取長度上限?**~~ → 上限 **4000 字元**。採分層截取策略 (§7.7)：焦點控制項 > 標題區塊 > 主要內容區塊,依預算逐層截取。
- [x] ~~**Q6: `content_summary` 由誰產出?**~~ → 主要由 M2.2 Gemma 邊緣 LLM 批次處理。**允許 rule-based fallback** (§7.8)：M2.2 離線時在本機截取焦點區塊標題 + 前 200 字作為 summary,標記 `inference_mode: "rule_based_fallback"`。M2.2 恢復後批次覆蓋為 LLM 版本。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責 (採集 + 去識別化),不能拆解
- [x] §2 至少 1 個 `Rxx` 引用 (R02 §1, R02 §1.2, R06 §2.1, R06 §7)
- [x] §3 Schema 用 Rust `serde` struct + `FocusSessionPayload` 定義
- [x] §4 依賴是真實模組編號 (M0.2, M0.4, M6.1, M1.2, M4.8)
- [x] §5 已 grep `05_integration_risk_audit.md`,觸發 **RISK-15** (Opt-in 內文摘要 → 草稿引用 → 雲端側通道洩漏),緩解策略已在 §5 與 `05_integration_risk_audit.md RISK-15` 記錄
- [x] §6 測試先於程式碼,覆蓋 11 個驗收條件 (驗收條件 5 已加 CaptureMode::Off 前提)
- [x] §8 至少 6 條反模式
- [x] §9 至少 4 個開放問題
