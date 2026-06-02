# M1.2 — 斷點偵測引擎 (Defer-to-Breakpoint Engine)

**標籤**: `[MVP]`
**版本**: `1.1`
**最後更新**: 2026-06-02

---

## 子模組 SPEC 決策說明

M1.2 包含三個子模組 (M1.2.1~M1.2.3),**合併為單一 SPEC** 的理由:

1. **串聯管線**:M1.2.1 偵測 → M1.2.2 門控 → M1.2.3 派發,三者是嚴格的單向管線,拆開後無法獨立驗收。
2. **共享 RISK**:RISK-04 的緩解策略橫跨三個子模組 (偵測時機 + 通知分類 + 派發策略),拆開會重複描述。
3. **同一行程**:三個子模組預計共存於同一模組內 (Rust crate 或 Python module),共享狀態機。

---

## 1. Purpose (目的)

精準偵測使用者的「任務斷點」(自然的認知中斷點),在低認知負荷時才允許系統推送通知,防範破壞性中斷對深度工作的傷害。

> 一句話:「**只在使用者準備好時才打擾,深度工作期間系統靜音**」。

---

## 2. References (引用研究)

| 編號 | 章節 | 應用點 |
| ---- | ---- | ------ |
| R08 | §二 任務斷點打斷管理 | Defer-to-Breakpoint 核心理論:在自然斷點推送通知,恢復延遲 (Resumption Lag) 降至最低 |
| R08 | §三 醫療級警報疲勞防範 | 通知三層分類 (L1 即時/L2 延遲/L3 安全),防止警報疲勞導致全部通知被忽略 |
| R08 | §一 認知負荷轉移 | 深度工作防擾鎖定器的理論基礎:高認知負荷時的中斷代價遠高於低負荷時 |

---

## 3. Inputs / Outputs

### Inputs

| 來源 | Schema | 範例 |
| ---- | ------ | ---- |
| M1.1 `focus_session_ended` 事件 | `FocusSessionEvent` | `{ duration_s: 1823, app_bucket: "coding", wpm_avg: 48, activity_state: "DEEP_FOCUS" }` |
| M1.1 `keystroke_burst` 事件 | `TelemetryEvent` | `{ action: "keystroke_burst", payload: { wpm_avg: 65 } }` |
| M1.1 `window_changed` 事件 | `TelemetryEvent` | `{ action: "window_changed", payload: { from: "Code", to: "Chrome" } }` |
| M1.1 `daemon_heartbeat` | `TelemetryEvent` | 每 30 秒,確認守護行程存活 |
| M1.1 `activity_state_changed` | `ActivityStateEvent` | `{ prev_state: "ACTIVE", new_state: "DEEP_FOCUS", confidence: 0.85 }` |
| M1.3.1 `ide_focus_leave` (選配) | `TelemetryEvent` | `{ module: "M1.3.1", action: "ide_focus_leave" }` — IDE 焦點離開事件,觸發 `BreakpointType::IDE_FOCUS_LEAVE` |

### Outputs

| 對象 | Schema | 範例 |
| ---- | ------ | ---- |
| Tauri 廣播 `BREAKPOINT_DETECTED` | `BreakpointEvent` | `{ type: "app_switch", confidence: 0.85, timestamp: "..." }` |
| M3.9 (通知儀表板) | 訂閱 `BREAKPOINT_DETECTED` | 收到後透過錯開調度器 (§7.6) 釋放排隊中的 L2 通知 |
| M4.4 (反思草稿) | 訂閱 `BREAKPOINT_DETECTED` | 收到後可觸發套問對話 |
| M0.4 → `raw_tracking_logs` | `TelemetryEvent` | `{ module: "M1.2", action: "breakpoint_detected", payload: {...} }` |

---

## 4. Dependencies

### 上游 (我依賴誰)

- **M1.1** (OS 遙測): 提供焦點/鍵鼠/視窗/ActivityState 事件流,是斷點偵測的主要輸入源
- **M1.3.1** (VS Code 擴充, 選配): 提供 `ide_focus_leave` 事件,觸發 `BreakpointType::IDE_FOCUS_LEAVE`;M1.3.1 未安裝時降級為 M1.1 的 `window_changed` 訊號
- **M0.2** (Tauri IPC): 透過 M0.2.2 通道廣播 `BREAKPOINT_DETECTED` 事件至前端
- **M0.4** (結構化日誌): 記錄斷點偵測事件至 `raw_tracking_logs`

### 下游 (誰依賴我)

- **M3.9** (通知儀表板): 收到斷點訊號後釋放 L2 延遲通知
- **M4.4** (反思草稿觸發): 在斷點時觸發自然套問
- **M1.5** (微 Nudges): 在斷點時推播微型問卷

---

## 5. Known Risks (整合風險)

| 風險編號 | 描述 | 緩解策略 |
| -------- | ---- | -------- |
| **RISK-04** | Defer-to-Breakpoint + 即時 XP 慶祝 → 動機脫節。若所有通知都延遲,Gacha 結果 30 分鐘後才看到 → 因果連結斷裂 | 通知三層分類:L1 即時 (使用者主動觸發) / L2 延遲 (系統主動推送) / L3 安全 (強制中斷)。僅 L2 走 Defer-to-Breakpoint |
| (無直接 RISK-xx) | M1.1 守護行程 crash → M1.2 持續收不到事件 → 誤以為使用者在深度工作 → 所有通知永遠不發 | 設置 10 秒無訊號 timeout:若 10 秒未收到 heartbeat,M1.2 進入 `degraded` 模式,允許所有通知通過 |
| (無直接 RISK-xx) | 斷點偵測過度靈敏 → 頻繁打斷 → 反而加劇警報疲勞 | 斷點事件設置最小間隔 (cooldown):兩次 `BREAKPOINT_DETECTED` 之間至少間隔 5 分鐘 |

---

## 6. Acceptance Criteria (驗收標準)

```python
# tests/m1_2/test_breakpoint_detection.py

class TestBreakpointDetection:
    def test_app_switch_triggers_breakpoint(self, engine, mock_events):
        """驗收條件 1: App 切換 (coding → browser) 觸發斷點"""
        engine.feed(focus_session_ended(app="Code", duration_s=1800))
        engine.feed(window_changed(from_app="Code", to_app="Chrome"))
        assert engine.last_breakpoint is not None
        assert engine.last_breakpoint.type == "app_switch"

    def test_idle_timeout_triggers_breakpoint(self, engine):
        """驗收條件 2: 5 分鐘無活動觸發斷點"""
        engine.feed(focus_session_ended(app="Code", duration_s=1800))
        engine.advance_time(seconds=300)  # 5 min idle
        assert engine.last_breakpoint.type == "idle_timeout"

    def test_wpm_drop_triggers_breakpoint(self, engine):
        """驗收條件 3: WPM 驟降 (>50% within 30s) 觸發斷點"""
        engine.feed(keystroke_burst(wpm_avg=60))
        engine.feed(keystroke_burst(wpm_avg=15))  # 75% drop
        assert engine.last_breakpoint.type == "wpm_drop"

    def test_deep_work_blocks_l2_notifications(self, engine, notification_queue):
        """驗收條件 4: 深度工作期間 L2 通知被攔截"""
        engine.feed(keystroke_burst(wpm_avg=70))  # High activity
        notification_queue.enqueue(type="L2", content="草稿已備妥")
        assert notification_queue.delivered_count == 0

    def test_l1_notification_bypasses_breakpoint(self, engine, notification_queue):
        """驗收條件 5: L1 即時通知 (Gacha) 不受斷點攔截 [RISK-04]"""
        engine.enter_deep_work()
        notification_queue.enqueue(type="L1", content="抽卡結果")
        assert notification_queue.delivered_count == 1

    def test_l3_safety_bypasses_breakpoint(self, engine, notification_queue):
        """驗收條件 6: L3 安全通知強制中斷 [RISK-04]"""
        engine.enter_deep_work()
        notification_queue.enqueue(type="L3", content="CARE 安全資源")
        assert notification_queue.delivered_count == 1

    def test_breakpoint_cooldown_5min(self, engine):
        """驗收條件 7: 兩次斷點間至少 5 分鐘"""
        engine.feed(window_changed(from_app="Code", to_app="Chrome"))
        first = engine.last_breakpoint
        engine.feed(window_changed(from_app="Chrome", to_app="Slack"))
        assert engine.last_breakpoint == first  # 未更新,cooldown 中

    def test_no_heartbeat_enters_degraded(self, engine):
        """驗收條件 8: 10 秒無 heartbeat → 降級模式,放行所有通知"""
        engine.advance_time(seconds=11)
        assert engine.mode == "degraded"

    def test_correct_breakpoint_rate_ge_80pct(self, engine, labeled_dataset):
        """驗收條件 9: 人工標註測試集斷點識別率 ≥80%"""
        correct = sum(1 for sample in labeled_dataset
                      if engine.predict(sample.events) == sample.is_breakpoint)
        assert correct / len(labeled_dataset) >= 0.80

    def test_staggered_notification_release(self, engine, notification_queue):
        """驗收條件 10: 斷點觸發時多 Persona 通知錯開釋放 (隨機延遲 1~60s)"""
        engine.feed(window_changed(from_app="Code", to_app="Chrome"))
        notification_queue.enqueue(type="L2", persona="Robert", content="反思草稿")
        notification_queue.enqueue(type="L2", persona="Beth", content="觀察洞察")
        notification_queue.enqueue(type="L2", persona="Observer", content="專案進展")
        release_times = notification_queue.get_scheduled_release_times()
        delays = [t - release_times[0] for t in release_times]
        # 每個通知的延遲應在 [0, 60] 秒範圍內
        assert all(0 <= d.total_seconds() <= 60 for d in delays)
        # 至少有兩個通知的延遲不同 (非同時釋放)
        assert len(set(d.total_seconds() for d in delays)) > 1

    def test_deep_work_stops_staggered_release(self, engine, notification_queue):
        """驗收條件 11: 通知錯開釋放中若重新進入 DEEP_WORK,停止釋放"""
        engine.feed(window_changed(from_app="Code", to_app="Chrome"))
        notification_queue.enqueue(type="L2", persona="Robert", content="草稿")
        notification_queue.enqueue(type="L2", persona="Beth", content="觀察")
        # 模擬使用者重新進入深度工作
        engine.feed(activity_state_changed(new_state="DEEP_FOCUS"))
        unreleased = notification_queue.get_pending_count()
        assert unreleased > 0  # 剩餘通知保留至下一個斷點

    def test_system_notification_restore_on_exit(self, engine):
        """驗收條件 12: 離開 DEEP_WORK 或系統登出時恢復系統通知"""
        engine.enter_deep_work()
        assert engine.system_notifications_muted is True
        engine.exit_deep_work()
        assert engine.system_notifications_muted is False

    def test_multi_signal_deep_work_entry(self, engine):
        """驗收條件 13: 多信號融合深度工作偵測 (不只靠 WPM)"""
        # 持續使用同一工作 app > 10 min,但 WPM = 0 (閱讀/Review)
        engine.feed(activity_state_changed(new_state="DEEP_FOCUS"))
        engine.feed(focus_session_ended(app="Code", duration_s=900, wpm_avg=0))
        assert engine.current_state == "DEEP_WORK"
```

---

## 7. Implementation Notes

### 7.1 子模組職責邊界

| 子模組 | 模組路徑 | 核心職責 |
| ------ | -------- | -------- |
| M1.2.1 | `breakpoint_detector.rs` / `.py` | 多訊號加權斷點偵測:接收 M1.1 事件流,計算斷點信心分數 |
| M1.2.2 | `deep_work_guard.rs` / `.py` | 深度工作防擾鎖定器:高認知負荷時攔截 L2 通知;管理 Windows 系統通知的靜音/恢復 |
| M1.2.3 | `breakpoint_dispatcher.rs` / `.py` | 斷點事件派發器:向 Tauri 廣播 `BREAKPOINT_DETECTED` 事件;管理 cooldown 計時器 |

### 7.2 斷點偵測狀態機

> v1.1 變更：DEEP_WORK 進入條件從單一 WPM 閾值升級為**多信號融合** (見下方說明)。

```
                  ┌──────────┐
                  │  IDLE    │ ← 無活動,所有通知放行
                  └────┬─────┘
                       │ keystroke_burst / focus_session
                       ▼
                  ┌──────────┐
                  │ ACTIVE   │ ← 正常活動,L2 通知排隊
                  └────┬─────┘
                       │ multi_signal_deep_work (見下方)
                       ▼
                  ┌──────────┐
                  │ DEEP_WORK│ ← 深度工作,L2 通知攔截 + 系統靜音 (Windows SetNotificationMode)
                  └────┬─────┘
                       │ app_switch / idle_5min / wpm_drop_50% / activity_state ∉ {DEEP_FOCUS, MEETING_CALL}
                       ▼
                  ┌──────────┐
                  │BREAKPOINT│ ← 派發事件 + 寫入 raw_tracking_logs,錯開釋放 L2 通知 (§7.6),cooldown 5min
                  └────┬─────┘
                       │ cooldown expired
                       ▼
                    回到 IDLE 或 ACTIVE
```

**多信號融合 DEEP_WORK 進入條件** (滿足任一組合)：

| 組合 | 條件 | 說明 |
|------|------|------|
| A | `activity_state == DEEP_FOCUS` | M1.1 八態分類器已判定深度專注 |
| B | `activity_state == MEETING_CALL` | 會議中不打擾 |
| C | WPM > `user_wpm_threshold` (預設 40,可配 20~80) + 持續 > 10 min | 傳統 WPM 方式,閾值可由使用者調配 |
| D | 視窗維持同一工作 app > 15 min + 焦點軟體屬固定工作組 + 無切換至娛樂類軟體 | 非打字型深度工作 (如 code review、設計) |

### 7.3 通知三層分類 [RISK-04]

| 類別 | 範例 | Defer? | 通道 |
| ---- | ---- | ------ | ---- |
| **L1 即時** | Gacha 結果、徽章解鎖 | ❌ 不 Defer | Toast 1.5s + 視覺特效 |
| **L2 系統洞察** | 反思草稿、Observer 觀察 | ✅ 必 Defer | 通知儀表板 (M3.9) |
| **L3 安全警示** | CARE 安全資源、隱私警告 | ❌ 不 Defer | Modal 強制中斷 |

### 7.4 BreakpointEvent Schema

```python
from pydantic import BaseModel
from enum import Enum
from datetime import datetime

class BreakpointType(str, Enum):
    APP_SWITCH = "app_switch"
    IDLE_TIMEOUT = "idle_timeout"
    WPM_DROP = "wpm_drop"
    IDE_FOCUS_LEAVE = "ide_focus_leave"

class BreakpointEvent(BaseModel):
    type: BreakpointType
    confidence: float              # 0.0~1.0
    timestamp: datetime
    preceding_app: str             # 斷點前的 app_bucket
    preceding_duration_s: int      # 斷點前的連續工作時長
```

### 7.5 異常處理

| 例外情況 | 處理方式 |
| -------- | -------- |
| M1.1 heartbeat 10 秒未到 | 進入 `degraded` 模式,所有通知放行,記錄 `level: "WARN"` |
| 斷點信心分數低於 0.5 | 不派發事件,繼續累積訊號 |
| Windows 通知靜音 API 失敗 | 記錄 `level: "WARN"`,M1.2.2 降級為「僅記錄不攔截」|
| cooldown 期間再次偵測到斷點 | 靜默忽略,不派發 |
| 離開 DEEP_WORK 狀態 | **立即恢復** Windows 系統通知 (`SetNotificationMode(normal)`) |
| 系統 logout / shutdown 事件 | **強制恢復** 系統通知 (Tauri close_request hook),防止靜音遺留 |
| 錯開釋放中使用者重新進入 DEEP_WORK | 停止釋放,剩餘 L2 通知保留至下一個斷點 |

### 7.6 斷點通知錯開調度器 (Staggered Notification Dispatcher) — v1.1 新增

斷點觸發時,排隊中的多個 AI 專家 (Persona) 的 L2 通知不能同時推送,需以隨機延遲錯開,避免一次性轟炸使用者。

```python
# services/m1_2_breakpoint/staggered_dispatcher.py
import random
import asyncio
from datetime import datetime, timedelta

class StaggeredNotificationDispatcher:
    """[RISK-04 緩解] 斷點觸發後,L2 通知隨機延遲 1~60 秒錯開釋放"""
    
    DELAY_MIN_S = 1
    DELAY_MAX_S = 60
    
    async def dispatch(self, pending_notifications: list, engine) -> list:
        """排隊中的 L2 通知按優先序排列,各自分配隨機延遲"""
        # 按優先序排列
        sorted_notifs = sorted(pending_notifications, key=lambda n: n.priority)
        released = []
        
        for notif in sorted_notifs:
            delay = random.uniform(self.DELAY_MIN_S, self.DELAY_MAX_S)
            await asyncio.sleep(delay)
            
            # 檢查使用者是否重新進入深度工作
            if engine.current_state == "DEEP_WORK":
                # 停止釋放,剩餘通知保留至下一個斷點
                break
            
            await self._release_notification(notif)
            released.append(notif)
        
        return released
```

**優先序定義**:
1. 最高：安全/健康相關 Persona (如 CARE)
2. 中高：使用者主動追蹤中的 Persona
3. 中等：反思草稿 (M4.4)
4. 低：一般觀察 (M4.6 Observer)

---

## 8. Anti-patterns (反模式)

- ❌ **不要對 L1 即時通知做 Defer** — 使用者主動觸發的操作 (Gacha、按鈕) 必須立即回饋,否則因果連結斷裂。`[RISK-04]`
- ❌ **不要在斷點偵測中讀取使用者內文** — M1.2 只消費 M1.1 的統計事件流 (WPM、app_bucket、duration、activity_state),不直接存取任何 L1 明文。
- ❌ **不要用固定時間間隔替代斷點偵測** — 「每 30 分鐘提醒一次」是反模式,會造成深度工作中斷。必須依據行為訊號判斷。`[R08 §二]`
- ❌ **不要在 DEEP_WORK 狀態播放任何聲音** — 包括系統音效、通知音效。M1.2.2 在進入 DEEP_WORK 時靜音系統通知 (`SetNotificationMode`),離開時必須恢復。
- ❌ **不要在斷點觸發時同時釋放所有 Persona 的 L2 通知** — 必須走錯開調度器 (§7.6),以隨機延遲 1~60 秒分批釋放,避免通知轟炸。若使用者重新進入 DEEP_WORK,立即停止釋放。

---

## 9. Open Questions

實作前必須與使用者拍板:

- [x] ~~**Q1: 深度工作判定的 WPM 閾值?**~~ → WPM 閾值**可由使用者調配** (預設 40,範圍 20~80)。且深度工作判定升級為**多信號融合** (§7.2)：WPM 僅為其中一個信號,同時融合 M1.1 的 `ActivityState` (DEEP_FOCUS / MEETING_CALL)、視窗維持時長、app 工作組一致性、是否切換至娛樂類軟體。現代工作越來越少純打字,故不能僅靠 WPM。
- [x] ~~**Q2: M1.2.2 是否真的要靜音系統通知?**~~ → **確認啟用**。進入 DEEP_WORK 時呼叫 Windows `SetNotificationMode` 靜音系統通知 (攔截 LINE、Slack 等)。離開 DEEP_WORK 或系統 logout/shutdown 時**自動恢復** (§7.5)。此功能需使用者在首次啟用時明確授權 (寫入 `user_consents` 表 `consent_type = 'system_notification_mute'`)。
- [x] ~~**Q3: 斷點事件是否寫入 raw_tracking_logs?**~~ → **確認寫入**。供 M4.4 統計「一天有多少個自然斷點」以及長期行為模式分析。寫入量可接受 (預估每天 10~30 個斷點事件)。

---

## SPEC 撰寫 Checklist

- [x] §1 Purpose 是單一職責 (斷點偵測 + 通知門控),不能拆解
- [x] §2 至少 1 個 `Rxx` 引用 (R08 §二, R08 §三, R08 §一)
- [x] §3 Schema 用 Pydantic `BreakpointEvent` 定義
- [x] §4 依賴是真實模組編號 (M1.1, M0.2, M0.4, M3.9, M4.4, M1.5)
- [x] §5 已 grep `05_integration_risk_audit.md`,觸發 RISK-04
- [x] §6 測試先於程式碼,覆蓋 13 個驗收條件 (含 v1.1 新增的錯開調度器、DEEP_WORK 重入、系統通知恢復、多信號偵測)
- [x] §8 至少 4 條反模式
- [x] §9 至少 3 個開放問題
