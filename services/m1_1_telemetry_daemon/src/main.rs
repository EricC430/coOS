/// M1.1 OS Telemetry Daemon — main entry point
///
/// SPEC: docs/modules/M1_1_os_telemetry_daemon_SPEC.md v1.2
/// Research: [R02: 計算心理語言學 §1] [R06: 數位表型 §2.1] [R07 §3]
///
/// Polling loop (500ms tick):
///   1. M1.1.1: poll foreground window → apply CaptureMode → emit window_changed on change
///   2. M1.1.2: accumulate keystroke counts → emit keystroke_burst every 5s
///   3. M1.1.3: update focus session → emit focus_session_ended on app switch
///   4. M1.1.3: emit heartbeat every 30s
///   5. M1.1.3: emit secondary_window_snapshot every 30s (EnumWindows)
///   6. M1.1.4: assert no hw capture on startup
///   7. Refresh CaptureConsent from FastAPI every 60s
use m1_1_telemetry_daemon::emitter::Emitter;
use m1_1_telemetry_daemon::m1_1_1_uiautomation::{
    fetch_capture_consent, get_foreground_window, process_window,
};
use m1_1_telemetry_daemon::m1_1_2_input_debouncer::InputDebouncer;
use m1_1_telemetry_daemon::m1_1_3_focus_tracker::FocusTracker;
use m1_1_telemetry_daemon::m1_1_4_privacy_guard::assert_no_hw_capture;
use m1_1_telemetry_daemon::models::{CaptureConsent, TelemetryEvent};

use std::time::{Duration, Instant};
use tokio::time::sleep;

const POLL_INTERVAL_MS: u64 = 500;
const BURST_EMIT_INTERVAL_S: u64 = 5;
/// Re-fetch CaptureConsent from FastAPI every 60 seconds so consent changes take effect.
const CONSENT_REFRESH_INTERVAL_S: u64 = 60;

#[tokio::main]
async fn main() {
    let http_client = reqwest::Client::new();
    let emitter = Emitter::new();
    let debouncer = InputDebouncer::new();
    let mut tracker = FocusTracker::new();

    // Spawn raw input keyboard listener thread for Windows
    m1_1_telemetry_daemon::m1_1_2_input_debouncer::spawn_raw_input_listener(debouncer.clone());

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

    // Initial consent fetch (defaults to Off on failure)
    let mut consent: CaptureConsent = fetch_capture_consent(&http_client).await;
    let mut last_consent_refresh = Instant::now();

    let mut last_app = String::new();
    let mut last_burst_emit = Instant::now();

    loop {
        sleep(Duration::from_millis(POLL_INTERVAL_MS)).await;

        // Periodically refresh CaptureConsent so user opt-in changes propagate
        if last_consent_refresh.elapsed().as_secs() >= CONSENT_REFRESH_INTERVAL_S {
            consent = fetch_capture_consent(&http_client).await;
            last_consent_refresh = Instant::now();
        }

        // M1.1.1: Poll foreground window
        if let Some(win) = get_foreground_window() {
            let is_foreground = win.app_name != "Unknown";
            debouncer.set_foreground_active(is_foreground);

            // Apply CaptureMode policy — produces WindowCapture with optional content
            let capture = process_window(&win, &consent);

            if win.app_name != last_app {
                // App switched
                let wpm = debouncer.current_wpm();
                let key_count = debouncer.drain_key_count();

                if key_count > 0 || wpm > 0.0 {
                    // [M1.1 SPEC §7.5] Activity before app switch resets idle timer
                    tracker.record_activity();
                    let burst_ev = TelemetryEvent::new(
                        "M1.1.2",
                        "keystroke_burst",
                        serde_json::json!({
                            "wpm_avg": wpm,
                            "key_count": key_count,
                        }),
                    );
                    emitter.emit(burst_ev).await;
                }

                // Emit focus_session_ended for previous app if long enough
                if let Some(session_ev) = tracker.on_focus_changed(
                    &win.app_name,
                    win.app_bucket.clone(),
                    wpm,
                    0,   // mouse_clicks — Phase 5+
                    0.0, // mouse_distance_norm — Phase 5+
                ) {
                    emitter.emit(session_ev).await;
                }

                // Emit window_changed — payload varies by CaptureMode
                // [M1.1 SPEC §8] CaptureMode::Off: no window_title in payload
                let mut ev_payload = serde_json::json!({
                    "app_name": capture.app_name,
                    "app_bucket": capture.app_bucket,
                });
                if let Some(title) = &capture.window_title {
                    ev_payload["window_title"] = serde_json::Value::String(title.clone());
                }
                // [RISK-15] content_raw is L1-only — it enters the local event payload
                // and local SQLite raw_tracking_logs, but is never synced to L3 (cloud).
                if let Some(summary) = &capture.content_summary {
                    if !is_browser_process(&capture.app_name) {
                        let content_ev = TelemetryEvent::new(
                            "M1.1.1",
                            "content_capture",
                            serde_json::json!({
                                "app_name": capture.app_name,
                                "content_raw": capture.content_raw,
                                "content_summary": summary,
                                "inference_mode": "rule_based_fallback",
                                "privacy_tier": "T1_OPTIN",
                            }),
                        );
                        emitter.emit(content_ev).await;
                    }
                }

                let ev = TelemetryEvent::new("M1.1.1", "window_changed", ev_payload);
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
                // [M1.1 SPEC §7.5] Keystroke activity resets idle timer for ActivityStateClassifier
                tracker.record_activity();
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

        // M1.1.3: Secondary window scan (EnumWindows every 30s)
        if let Some(scan_ev) = tracker.tick_secondary_scan() {
            emitter.emit(scan_ev).await;
        }
    }
}

fn is_browser_process(app_name: &str) -> bool {
    let lower = app_name.to_lowercase();
    lower == "chrome.exe"
        || lower == "msedge.exe"
        || lower == "firefox.exe"
        || lower == "brave.exe"
        || lower == "opera.exe"
        || lower == "chrome"
        || lower == "msedge"
        || lower == "firefox"
        || lower == "brave"
}
