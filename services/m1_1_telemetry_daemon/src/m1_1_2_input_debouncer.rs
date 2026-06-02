/// M1.1.2 Global Keystroke/Mouse Debounce Listener
///
/// SPEC: docs/modules/M1_1_os_telemetry_daemon_SPEC.md §7.1 M1.1.2
/// [R02: 計算心理語言學 §1] WPM as cognitive state input feature.
///
/// Privacy: only statistical counts (key_count, wpm) are recorded.
/// Raw keystroke sequences are NEVER stored.
use crate::models::WpmCalculator;
use std::sync::{Arc, Mutex};
use std::time::{SystemTime, UNIX_EPOCH};

pub struct InputDebouncer {
    wpm_calc: Arc<Mutex<WpmCalculator>>,
    key_count_window: Arc<Mutex<u32>>,
    is_foreground_active: Arc<Mutex<bool>>,
}

impl InputDebouncer {
    pub fn new() -> Self {
        Self {
            wpm_calc: Arc::new(Mutex::new(WpmCalculator::new())),
            key_count_window: Arc::new(Mutex::new(0)),
            is_foreground_active: Arc::new(Mutex::new(false)),
        }
    }

    pub fn set_foreground_active(&self, active: bool) {
        *self.is_foreground_active.lock().unwrap() = active;
        if !active {
            // [M1.1 SPEC §8] Reset WPM on focus change — prevents cross-app pollution
            self.wpm_calc.lock().unwrap().reset();
        }
    }

    /// Called on each Raw Input keyboard event.
    /// [M1.1 SPEC §8] Only accumulates when foreground is active.
    pub fn on_key_event(&self, key_count: u32) {
        if !*self.is_foreground_active.lock().unwrap() {
            return; // [M1.1 SPEC §8] Never accumulate when not in foreground
        }
        let now_ms = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;
        let mut calc = self.wpm_calc.lock().unwrap();
        calc.push(key_count, now_ms);
        *self.key_count_window.lock().unwrap() += key_count;
    }

    pub fn current_wpm(&self) -> f32 {
        self.wpm_calc.lock().unwrap().current_wpm()
    }

    pub fn drain_key_count(&self) -> u32 {
        let mut count = self.key_count_window.lock().unwrap();
        let val = *count;
        *count = 0;
        val
    }
}

impl Default for InputDebouncer {
    fn default() -> Self {
        Self::new()
    }
}
