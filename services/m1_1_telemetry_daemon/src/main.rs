/// M1.1 OS Telemetry Daemon — main entry point
///
/// SPEC: docs/modules/M1_1_os_telemetry_daemon_SPEC.md v1.2
/// Research: [R02: 計算心理語言學 §1] [R06: 數位表型 §2.1]
///
/// Polling loop (10ms tick):
///   1. M1.1.1: poll foreground window → emit window_changed on change
///   2. M1.1.2: accumulate keystroke counts → emit keystroke_burst every 5s
///   3. M1.1.3: update focus session → emit focus_session_ended on app switch
///   4. M1.1.3: emit heartbeat every 30s
///   5. M1.1.4: assert no hw capture on startup
use m1_1_telemetry_daemon::emitter::Emitter;
use m1_1_telemetry_daemon::m1_1_1_uiautomation::get_foreground_window;
use m1_1_telemetry_daemon::m1_1_2_input_debouncer::InputDebouncer;
use m1_1_telemetry_daemon::m1_1_3_focus_tracker::FocusTracker;
use m1_1_telemetry_daemon::m1_1_4_privacy_guard::assert_no_hw_capture;
use m1_1_telemetry_daemon::models::{AppBucket, TelemetryEvent};

use std::time::{Duration, Instant};
use tokio::time::sleep;

const POLL_INTERVAL_MS: u64 = 500;   // Poll every 500ms
const BURST_EMIT_INTERVAL_S: u64 = 5; // Emit keystroke_burst every 5s

#[tokio::main]
async fn main() {
    let emitter = Emitter::new();
    let debouncer = InputDebouncer::new();
    let mut tracker = FocusTracker::new();

    // M1.1.4: Privacy assertion at startup
    let guard = assert_no_hw_capture();
    if !guard.camera_clean || !guard.microphone_clean {
        let ev = TelemetryEvent::warn(
            "M1.1.4",
            "privacy_assertion_failed",
            serde_json::json!({
                "camera_clean": guard.camera_clean,
                "microphone_clean": guard.microphone_clean,
            }),
        );
        emitter.emit(ev).await;
    } else {
        let ev = TelemetryEvent::new("M1.1.4", "privacy_assertion_passed", serde_json::json!({}));
        emitter.emit(ev).await;
    }

    let mut last_app = String::new();
    let mut last_burst_emit = Instant::now();

    loop {
        sleep(Duration::from_millis(POLL_INTERVAL_MS)).await;

        // M1.1.1: Poll foreground window
        if let Some(win) = get_foreground_window() {
            let is_foreground = win.app_name != "Unknown";
            debouncer.set_foreground_active(is_foreground);

            if win.app_name != last_app {
                // App switched
                let wpm = debouncer.current_wpm();
                let key_count = debouncer.drain_key_count();

                // Emit focus_session_ended for previous app if long enough
                if let Some(session_ev) = tracker.on_focus_changed(
                    &win.app_name,
                    win.app_bucket.clone(),
                    wpm,
                    0, // mouse_clicks — Phase 5+
                    0.0,
                ) {
                    emitter.emit(session_ev).await;
                }

                // Emit window_changed
                let ev = TelemetryEvent::new(
                    "M1.1.1",
                    "window_changed",
                    serde_json::json!({
                        "app_name": win.app_name,
                        "app_bucket": win.app_bucket,
                    }),
                );
                emitter.emit(ev).await;
                last_app = win.app_name;
            }
        } else {
            debouncer.set_foreground_active(false);
        }

        // M1.1.2: Emit keystroke_burst every 5s
        if last_burst_emit.elapsed().as_secs() >= BURST_EMIT_INTERVAL_S {
            let wpm = debouncer.current_wpm();
            let key_count = debouncer.drain_key_count();
            if key_count > 0 || wpm > 0.0 {
                let ev = TelemetryEvent::new(
                    "M1.1.2",
                    "keystroke_burst",
                    serde_json::json!({
                        "wpm_avg": wpm,
                        "key_count": key_count,
                    }),
                );
                emitter.emit(ev).await;
            }
            last_burst_emit = Instant::now();
        }

        // M1.1.3: Heartbeat tick
        if let Some(hb) = tracker.tick_heartbeat() {
            emitter.emit(hb).await;
        }
    }
}
