/// M1.1.1 UIAutomation API Bridge
///
/// SPEC: docs/modules/M1_1_os_telemetry_daemon_SPEC.md §7.1 M1.1.1
/// [R06: 數位表型 §2.1] Process name as digital phenotype sensor input.
///
/// CaptureMode::Off (Phase 3 default): only process name + app_bucket.
/// window_title and content_raw are never captured in this mode.
use crate::models::{classify_process, AppBucket};

pub struct ForegroundWindow {
    pub app_name: String,
    pub app_bucket: AppBucket,
}

#[cfg(windows)]
pub fn get_foreground_window() -> Option<ForegroundWindow> {
    use windows::Win32::Foundation::HWND;
    use windows::Win32::System::Threading::{GetCurrentProcessId, OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION};
    use windows::Win32::UI::WindowsAndMessaging::{GetForegroundWindow, GetWindowThreadProcessId};
    use windows::Win32::System::ProcessStatus::GetProcessImageFileNameW;

    unsafe {
        let hwnd: HWND = GetForegroundWindow();
        if hwnd.0.is_null() {
            return None;
        }

        let mut pid: u32 = 0;
        GetWindowThreadProcessId(hwnd, Some(&mut pid));
        if pid == 0 {
            return None;
        }

        // Get process name — gracefully skip on AccessDenied
        let process_name = match OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) {
            Ok(handle) => {
                let mut buf = vec![0u16; 260];
                let len = GetProcessImageFileNameW(handle, &mut buf);
                if len == 0 {
                    "Unknown".to_string()
                } else {
                    let path: String = String::from_utf16_lossy(&buf[..len as usize]);
                    // Extract just the filename
                    path.split(['\\', '/']).last().unwrap_or("Unknown").to_string()
                }
            }
            Err(_) => {
                // AccessDenied — record as Unknown, do not panic
                "Unknown".to_string()
            }
        };

        let bucket = classify_process(&process_name);
        Some(ForegroundWindow { app_name: process_name, app_bucket: bucket })
    }
}

#[cfg(not(windows))]
pub fn get_foreground_window() -> Option<ForegroundWindow> {
    // Non-Windows stub — always returns None in tests/dev on non-Windows
    None
}
