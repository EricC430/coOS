/// M1.1 TelemetryEvent models
///
/// SPEC: docs/modules/M1_1_os_telemetry_daemon_SPEC.md §7.2
/// Matches M0.4 LogEvent schema so FastAPI can validate with Pydantic.
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
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

/// [R06: 數位表型 §2.1] Eight-state activity classifier output.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ActivityState {
    /// Single work app focused > 10 min, stable WPM, no entertainment switches
    DeepFocus,
    /// Normal keyboard/mouse activity
    Active,
    /// Fullscreen media + no input > 2 min
    PassiveConsumption,
    /// High scroll rate + short page stay + social/entertainment + >= 5 min
    DoomScrolling,
    /// >= 4 app switches in 5 min, each < 60s
    ContextSwitching,
    /// Browser/PDF + low WPM + page stay > 2 min + non-entertainment
    ResearchReading,
    /// Video/voice call app foreground > 5 min
    MeetingCall,
    /// No keyboard/mouse > 5 min
    Idle,
}

/// M0.4-compatible LogEvent (matches Pydantic LogEvent schema).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TelemetryEvent {
    pub id: String,
    pub timestamp: String,   // ISO 8601 UTC
    pub module: String,      // "M1.1.1" | "M1.1.2" | "M1.1.3" | "M1.1.4"
    pub action: String,
    pub level: String,       // "INFO" | "WARNING" | "ERROR"
    pub payload: serde_json::Value,
    pub role_id: Option<String>,
    pub correlation_id: Option<String>,
}

impl TelemetryEvent {
    pub fn new(module: &str, action: &str, payload: serde_json::Value) -> Self {
        Self {
            id: uuid::Uuid::new_v4().to_string(),
            timestamp: chrono::Utc::now().to_rfc3339(),
            module: module.to_string(),
            action: action.to_string(),
            level: "INFO".to_string(),
            payload,
            role_id: None,
            correlation_id: None,
        }
    }

    pub fn warn(module: &str, action: &str, payload: serde_json::Value) -> Self {
        let mut ev = Self::new(module, action, payload);
        ev.level = "WARNING".to_string();
        ev
    }
}

/// [R02: 計算心理語言學 §1] WPM sliding-window calculator.
/// 60-second fixed window; resets on focus change.
pub struct WpmCalculator {
    /// (timestamp_ms, key_count_delta) pairs in the window
    window: std::collections::VecDeque<(u64, u32)>,
    window_ms: u64,
}

impl WpmCalculator {
    const AVG_CHARS_PER_WORD: f32 = 5.0;

    pub fn new() -> Self {
        Self {
            window: std::collections::VecDeque::new(),
            window_ms: 60_000,
        }
    }

    pub fn push(&mut self, key_count: u32, now_ms: u64) {
        self.window.push_back((now_ms, key_count));
        while let Some(&(ts, _)) = self.window.front() {
            if now_ms.saturating_sub(ts) > self.window_ms {
                self.window.pop_front();
            } else {
                break;
            }
        }
    }

    /// Returns current WPM based on keys in the 60s window.
    pub fn current_wpm(&self) -> f32 {
        let total: u32 = self.window.iter().map(|(_, k)| k).sum();
        total as f32 / Self::AVG_CHARS_PER_WORD
    }

    pub fn reset(&mut self) {
        self.window.clear();
    }
}

/// Map Windows process name → AppBucket.
pub fn classify_process(process_name: &str) -> AppBucket {
    let lower = process_name.to_lowercase();
    let lower = lower.trim_end_matches(".exe");
    match lower {
        "code" | "cursor" | "rider" | "clion" | "pycharm" | "idea"
        | "devenv" | "sublime_text" | "atom" | "notepad++" => AppBucket::Coding,
        "winword" | "soffice" | "notion" | "obsidian" | "typora"
        | "onenote" => AppBucket::Writing,
        "chrome" | "firefox" | "msedge" | "opera" | "brave"
        | "safari" | "vivaldi" | "acrobat" | "sumatra" => AppBucket::Reading,
        "slack" | "teams" | "discord" | "telegram" | "whatsapp"
        | "outlook" | "thunderbird" | "mattermost" => AppBucket::Communication,
        "excel" | "powerpoint" | "calc" | "impress" | "airtable"
        | "trello" | "asana" | "jira" | "linear" => AppBucket::Productivity,
        _ => AppBucket::Unknown,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_wpm_60s_window() {
        // [R02: 計算心理語言學 §1] 300 keys / 5 chars/word = 60 WPM
        let mut calc = WpmCalculator::new();
        let base_ms: u64 = 1_000_000;
        // Spread 300 keystrokes over 60 seconds
        for i in 0..60u64 {
            calc.push(5, base_ms + i * 1000);
        }
        let wpm = calc.current_wpm();
        assert!((55.0..=65.0).contains(&wpm), "Expected ~60 WPM, got {wpm}");
    }

    #[test]
    fn test_wpm_resets_on_focus_change() {
        let mut calc = WpmCalculator::new();
        calc.push(100, 1_000_000);
        assert!(calc.current_wpm() > 0.0);
        calc.reset();
        assert_eq!(calc.current_wpm(), 0.0);
    }

    #[test]
    fn test_wpm_evicts_old_entries() {
        let mut calc = WpmCalculator::new();
        // Push old entry (ts = 0)
        calc.push(300, 0);
        // Push new entry 70 seconds later (ts = 70_000ms) — old entry should be evicted
        calc.push(5, 70_000);
        let wpm = calc.current_wpm();
        // Only 5 keys in window → 5/5 = 1 WPM
        assert!(wpm < 5.0, "Old entries should be evicted, got {wpm}");
    }

    #[test]
    fn test_classify_process_coding() {
        assert_eq!(classify_process("Code.exe"), AppBucket::Coding);
        assert_eq!(classify_process("cursor.exe"), AppBucket::Coding);
    }

    #[test]
    fn test_classify_process_communication() {
        assert_eq!(classify_process("slack.exe"), AppBucket::Communication);
        assert_eq!(classify_process("Discord.exe"), AppBucket::Communication);
    }

    #[test]
    fn test_classify_process_unknown() {
        assert_eq!(classify_process("Taskmgr.exe"), AppBucket::Unknown);
        assert_eq!(classify_process("notepad.exe"), AppBucket::Unknown);
    }

    #[test]
    fn test_telemetry_event_new() {
        let ev = TelemetryEvent::new("M1.1.3", "daemon_heartbeat", serde_json::json!({}));
        assert_eq!(ev.module, "M1.1.3");
        assert_eq!(ev.level, "INFO");
        assert!(!ev.id.is_empty());
    }

    #[test]
    fn test_activity_state_serializes_screaming_snake() {
        let state = ActivityState::DeepFocus;
        let json = serde_json::to_string(&state).unwrap();
        assert_eq!(json, "\"DEEP_FOCUS\"");
    }
}
