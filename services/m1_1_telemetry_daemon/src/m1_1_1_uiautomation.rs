/// M1.1.1 UIAutomation API Bridge
///
/// SPEC: docs/modules/M1_1_os_telemetry_daemon_SPEC.md §7.1 M1.1.1, §7.3, §7.7, §7.8
/// [R06: 數位表型 §2.1] Process name as digital phenotype sensor input.
/// [R07 §3] Opt-in content capture via UIAutomation UIA_ValuePattern / UIA_TextPattern.
///
/// CaptureMode::Off (default): only process name + app_bucket. No title, no raw text.
/// CaptureMode::AllApps / SelectedApps: window_title + layered content_raw (≤ 4 000 chars).
/// content_raw is L1-only and NEVER leaves the device (RISK-15).
use crate::models::{classify_process, AppBucket, CaptureConsent, CaptureMode, WindowCapture};

const MAX_CONTENT_RAW_CHARS: usize = 4000;

#[cfg(windows)]
use windows::{
    Win32::UI::Accessibility::{AccessibleObjectFromWindow, IAccessible},
    Win32::UI::WindowsAndMessaging::OBJID_CLIENT,
    core::{VARIANT, Interface},
};

// ---------------------------------------------------------------------------
// Public surface
// ---------------------------------------------------------------------------

pub struct ForegroundWindow {
    pub app_name: String,
    pub app_bucket: AppBucket,
    /// Raw window title — only populated when CaptureMode != Off.
    pub window_title: Option<String>,
}

#[cfg(windows)]
pub fn get_foreground_window() -> Option<ForegroundWindow> {
    use windows::Win32::Foundation::HWND;
    use windows::Win32::System::Threading::{OpenProcess, PROCESS_QUERY_LIMITED_INFORMATION};
    use windows::Win32::UI::WindowsAndMessaging::{
        GetForegroundWindow, GetWindowTextW, GetWindowThreadProcessId,
    };
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

        // Capture raw window title for potential Opt-in use (also used for debug)
        let mut title_buf = vec![0u16; 512];
        let title_len = GetWindowTextW(hwnd, &mut title_buf);
        let window_title_raw = if title_len > 0 {
            Some(String::from_utf16_lossy(&title_buf[..title_len as usize]))
        } else {
            None
        };

        // Get process name — gracefully skip on AccessDenied
        let process_name = match OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid) {
            Ok(handle) => {
                let mut buf = vec![0u16; 260];
                let len = GetProcessImageFileNameW(handle, &mut buf);
                if len == 0 {
                    "Unknown".to_string()
                } else {
                    let path = String::from_utf16_lossy(&buf[..len as usize]);
                    path.split(['\\', '/']).last().unwrap_or("Unknown").to_string()
                }
            }
            Err(_) => "Unknown".to_string(),
        };

        eprintln!(
            "[M1.1.1 DEBUG] foreground: {:?} | process: {}",
            window_title_raw, process_name
        );

        let bucket = classify_process(&process_name);
        Some(ForegroundWindow {
            app_name: process_name,
            app_bucket: bucket,
            window_title: window_title_raw,
        })
    }
}

#[cfg(not(windows))]
pub fn get_foreground_window() -> Option<ForegroundWindow> {
    None
}

// ---------------------------------------------------------------------------
// process_window — applies CaptureMode policy  (SPEC §7.3)
// ---------------------------------------------------------------------------

/// [R07 §3] Apply CaptureMode to decide what to keep from a foreground window.
/// Returns a WindowCapture whose content_raw / content_summary are L1-only.
pub fn process_window(win: &ForegroundWindow, consent: &CaptureConsent) -> WindowCapture {
    match consent.mode {
        CaptureMode::Off => {
            // v1.0 behaviour: discard window title and all content
            WindowCapture {
                app_name: win.app_name.clone(),
                app_bucket: win.app_bucket.clone(),
                window_title: None,
                content_raw: None,
                content_summary: None,
            }
        }
        CaptureMode::AllApps => {
            let raw_title = win.window_title.clone();
            let content = read_focused_content_layered(&win.app_name, raw_title.as_deref());
            let summary = content
                .as_deref()
                .map(|r| generate_content_summary_fallback(r, raw_title.as_deref().unwrap_or("")));
            WindowCapture {
                app_name: win.app_name.clone(),
                app_bucket: win.app_bucket.clone(),
                window_title: raw_title,
                content_raw: content,
                // content_summary: None signals M2.2 to fill in the LLM version later;
                // rule-based fallback is only used when M2.2 is offline.
                content_summary: summary,
            }
        }
        CaptureMode::SelectedApps => {
            let name_lower = win.app_name.to_lowercase();
            let allowed = consent.allowed_processes.iter().any(|p| {
                p.to_lowercase() == name_lower
                    || p.to_lowercase() == name_lower.trim_end_matches(".exe")
            });
            if allowed {
                let raw_title = win.window_title.clone();
                let content = read_focused_content_layered(&win.app_name, raw_title.as_deref());
                let summary = content.as_deref().map(|r| {
                    generate_content_summary_fallback(r, raw_title.as_deref().unwrap_or(""))
                });
                WindowCapture {
                    app_name: win.app_name.clone(),
                    app_bucket: win.app_bucket.clone(),
                    window_title: raw_title,
                    content_raw: content,
                    content_summary: summary,
                }
            } else {
                // Not in allowlist — same as Off
                WindowCapture {
                    app_name: win.app_name.clone(),
                    app_bucket: win.app_bucket.clone(),
                    window_title: None,
                    content_raw: None,
                    content_summary: None,
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Layered content extraction  (SPEC §7.7)
// ---------------------------------------------------------------------------

/// [R07 §3] Extract up to MAX_CONTENT_RAW_CHARS of text from the foreground
/// window using UIAutomation patterns.  Layered: focus element → title bar → main content.
#[cfg(windows)]
fn read_focused_content_layered(_process_name: &str, window_title: Option<&str>) -> Option<String> {
    use windows::Win32::UI::Accessibility::{
        CUIAutomation, IUIAutomation,
    };
    use windows::Win32::UI::WindowsAndMessaging::GetForegroundWindow;

    let mut result = String::new();
    let mut budget = MAX_CONTENT_RAW_CHARS;

    unsafe {
        // Initialize COM on the current thread
        let _ = windows::Win32::System::Com::CoInitializeEx(
            None,
            windows::Win32::System::Com::COINIT_APARTMENTTHREADED,
        );

        // Initialise UIAutomation COM object
        let automation: IUIAutomation = match windows::Win32::System::Com::CoCreateInstance(
            &CUIAutomation,
            None,
            windows::Win32::System::Com::CLSCTX_INPROC_SERVER,
        ) {
            Ok(a) => a,
            Err(e) => {
                eprintln!("[M1.1.1 WARN] CoCreateInstance IUIAutomation failed: {e:?}");
                // Fallback: use window title as summary
                if let Some(title) = window_title {
                    return Some(format!("[TITLE] {}", &title[..title.len().min(200)]));
                }
                return None;
            }
        };

        let hwnd = GetForegroundWindow();
        if hwnd.0.is_null() {
            return None;
        }

        // Layer 1: focused element text (with Mouse Hover fallback)
        let mut focus_text = None;
        if let Ok(focus_elem) = automation.GetFocusedElement() {
            focus_text = extract_element_text(&focus_elem);
        }

        // Fallback: If focused element has no text, try ElementFromPoint (Hover)
        if focus_text.is_none() {
            use windows::Win32::Foundation::POINT;
            use windows::Win32::UI::WindowsAndMessaging::GetCursorPos;
            let mut pt = POINT::default();
            if GetCursorPos(&mut pt).is_ok() {
                if let Ok(hover_elem) = automation.ElementFromPoint(pt) {
                    if let Some(text) = extract_element_text(&hover_elem) {
                        focus_text = Some(text);
                    } else if let Ok(bstr) = hover_elem.CurrentName() {
                        let name = bstr.to_string();
                        if !name.trim().is_empty() {
                            focus_text = Some(name);
                        }
                    }
                }
            }
        }

        if let Some(text) = focus_text {
            let chunk = truncate_chars(&text, budget);
            result.push_str("[FOCUS] ");
            result.push_str(&chunk);
            budget = budget.saturating_sub(chunk.chars().count() + 8);
        }

        // Layer 2: window title bar (passed in from GetWindowTextW, already have it)
        if budget > 0 {
            if let Some(title) = window_title {
                let chunk = truncate_chars(title, budget.min(200));
                result.push_str("\n[TITLE] ");
                result.push_str(&chunk);
                budget = budget.saturating_sub(chunk.chars().count() + 9);
            }
        }

        // Layer 3: main content element from window root (with Control Tree Traversal fallback)
        if budget > 0 {
            if let Ok(root) = automation.ElementFromHandle(hwnd) {
                let mut root_text = extract_element_text(&root);
                if root_text.is_none() {
                    if let Ok(walker) = automation.ControlViewWalker() {
                        let mut collected = String::new();
                        let mut char_budget = 2000;
                        let mut node_limit = 50;
                        traverse_control_tree(&root, &walker, &mut collected, &mut char_budget, &mut node_limit);
                        if !collected.is_empty() {
                            root_text = Some(collected);
                        }
                    }
                }

                if let Some(text) = root_text {
                    let chunk = truncate_chars(&text, budget);
                    result.push_str("\n[MAIN] ");
                    result.push_str(&chunk);
                    budget = budget.saturating_sub(chunk.chars().count() + 8);
                }
            }
        }

        // Layer 4: MSAA Fallback
        if budget > 0 && result.lines().count() <= 2 {
            if let Some(msaa_text) = get_msaa_content(hwnd) {
                let chunk = truncate_chars(&msaa_text, budget);
                result.push_str("\n[MAIN_MSAA] ");
                result.push_str(&chunk);
            }
        }
    }

    if result.is_empty() {
        None
    } else {
        Some(result)
    }
}

/// Recursively walk the UIA tree walker to find text-bearing controls
#[cfg(windows)]
unsafe fn traverse_control_tree(
    elem: &windows::Win32::UI::Accessibility::IUIAutomationElement,
    walker: &windows::Win32::UI::Accessibility::IUIAutomationTreeWalker,
    collected: &mut String,
    char_budget: &mut usize,
    node_limit: &mut usize,
) {
    if *char_budget == 0 || *node_limit == 0 {
        return;
    }
    *node_limit -= 1;

    if let Ok(control_type) = elem.CurrentControlType() {
        use windows::Win32::UI::Accessibility::{
            UIA_EditControlTypeId, UIA_DocumentControlTypeId, UIA_TextControlTypeId,
            UIA_DataItemControlTypeId, UIA_ListControlTypeId
        };
        if control_type == UIA_EditControlTypeId
            || control_type == UIA_DocumentControlTypeId
            || control_type == UIA_TextControlTypeId
            || control_type == UIA_DataItemControlTypeId
            || control_type == UIA_ListControlTypeId
        {
            if let Ok(bstr) = elem.CurrentName() {
                let name = bstr.to_string();
                let trimmed = name.trim();
                if !trimmed.is_empty() && !collected.contains(trimmed) {
                    if !collected.is_empty() {
                        collected.push(' ');
                    }
                    let chunk = truncate_chars(trimmed, *char_budget);
                    collected.push_str(&chunk);
                    *char_budget = char_budget.saturating_sub(chunk.chars().count() + 1);
                }
            }
        }
    }

    if *char_budget > 0 && *node_limit > 0 {
        if let Ok(child) = walker.GetFirstChildElement(elem) {
            traverse_control_tree(&child, walker, collected, char_budget, node_limit);
            let mut sibling = child;
            while *char_budget > 0 && *node_limit > 0 {
                if let Ok(next) = walker.GetNextSiblingElement(&sibling) {
                    traverse_control_tree(&next, walker, collected, char_budget, node_limit);
                    sibling = next;
                } else {
                    break;
                }
            }
        }
    }
}

/// Fetch MSAA text content recursively using Microsoft Active Accessibility
#[cfg(windows)]
fn get_msaa_content(hwnd: windows::Win32::Foundation::HWND) -> Option<String> {
    unsafe {
        let mut ppvobject: *mut std::ffi::c_void = std::ptr::null_mut();
        if AccessibleObjectFromWindow(
            hwnd,
            OBJID_CLIENT.0 as u32,
            &IAccessible::IID,
            &mut ppvobject,
        ).is_ok() {
            if !ppvobject.is_null() {
                let accessible: IAccessible = std::mem::transmute(ppvobject);
                let mut collected = String::new();
                let mut char_budget = 2000;
                let mut node_limit = 50;
                let var_self = VARIANT::from(0i32);
                traverse_msaa(&accessible, &var_self, &mut collected, &mut char_budget, &mut node_limit);
                if !collected.is_empty() {
                    return Some(collected);
                }
            }
        }
    }
    None
}

/// Recursively traverse the IAccessible node tree to gather names and values
#[cfg(windows)]
unsafe fn traverse_msaa(
    acc: &IAccessible,
    var_self: &VARIANT,
    collected: &mut String,
    char_budget: &mut usize,
    node_limit: &mut usize,
) {
    if *char_budget == 0 || *node_limit == 0 {
        return;
    }
    *node_limit -= 1;

    // Get accessible Name
    if let Ok(name_bstr) = acc.get_accName(var_self) {
        let name = name_bstr.to_string();
        let trimmed = name.trim();
        if !trimmed.is_empty() && !collected.contains(trimmed) {
            if !collected.is_empty() {
                collected.push(' ');
            }
            let chunk = truncate_chars(trimmed, *char_budget);
            collected.push_str(&chunk);
            *char_budget = char_budget.saturating_sub(chunk.chars().count() + 1);
        }
    }

    // Get accessible Value
    if *char_budget > 0 {
        if let Ok(val_bstr) = acc.get_accValue(var_self) {
            let val = val_bstr.to_string();
            let trimmed = val.trim();
            if !trimmed.is_empty() && !collected.contains(trimmed) {
                if !collected.is_empty() {
                    collected.push(' ');
                }
                let chunk = truncate_chars(trimmed, *char_budget);
                collected.push_str(&chunk);
                *char_budget = char_budget.saturating_sub(chunk.chars().count() + 1);
            }
        }
    }

    // Recursively walk children
    if let Ok(child_count) = acc.accChildCount() {
        if child_count > 0 && *char_budget > 0 && *node_limit > 0 {
            for i in 1..=child_count {
                if *char_budget == 0 || *node_limit == 0 {
                    break;
                }
                let var_child = VARIANT::from(i);
                if let Ok(child_dispatch) = acc.get_accChild(&var_child) {
                    if let Ok(child_acc) = child_dispatch.cast::<IAccessible>() {
                        let var_child_self = VARIANT::from(0i32);
                        traverse_msaa(&child_acc, &var_child_self, collected, char_budget, node_limit);
                    }
                }
            }
        }
    }
}

/// Extract text from a UIAutomation element via ValuePattern or TextPattern.
#[cfg(windows)]
fn extract_element_text(
    elem: &windows::Win32::UI::Accessibility::IUIAutomationElement,
) -> Option<String> {
    use windows::Win32::UI::Accessibility::{
        IUIAutomationTextPattern, IUIAutomationValuePattern,
        UIA_ValuePatternId, UIA_TextPatternId,
    };

    unsafe {
        // Try ValuePattern first (text boxes, inputs)
        if let Ok(pattern) = elem.GetCurrentPatternAs::<IUIAutomationValuePattern>(UIA_ValuePatternId) {
            if let Ok(bstr) = pattern.CurrentValue() {
                let s = bstr.to_string();
                if !s.is_empty() {
                    return Some(s);
                }
            }
        }
        // Fallback to TextPattern (documents, editors)
        if let Ok(pattern) = elem.GetCurrentPatternAs::<IUIAutomationTextPattern>(UIA_TextPatternId) {
            if let Ok(range) = pattern.DocumentRange() {
                if let Ok(bstr) = range.GetText(4000) {
                    let s = bstr.to_string();
                    if !s.is_empty() {
                        return Some(s);
                    }
                }
            }
        }
        None
    }
}

#[cfg(not(windows))]
fn read_focused_content_layered(_process_name: &str, _window_title: Option<&str>) -> Option<String> {
    None
}

// ---------------------------------------------------------------------------
// Rule-based content_summary fallback  (SPEC §7.8)
// ---------------------------------------------------------------------------

/// [R07 §3] When M2.2 Gemma is offline, produce a lightweight summary from
/// content_raw: title bar prefix + first 200 chars of [FOCUS] block.
/// Marked inference_mode = "rule_based_fallback" so M2.2 can overwrite later.
pub fn generate_content_summary_fallback(content_raw: &str, window_title: &str) -> String {
    let mut summary = String::new();

    // Use [TITLE] block if present, otherwise fall back to window_title argument
    if let Some(title_start) = content_raw.find("[TITLE] ") {
        let rest = &content_raw[title_start + 8..];
        let end = rest.find('\n').unwrap_or(rest.len());
        summary.push_str(rest[..end].trim());
        summary.push_str(" — ");
    } else if !window_title.is_empty() {
        summary.push_str(window_title);
        summary.push_str(" — ");
    }

    // First 200 chars of [FOCUS] block, or plain start
    if let Some(focus_start) = content_raw.find("[FOCUS] ") {
        let rest = &content_raw[focus_start + 8..];
        let end = rest.find('\n').unwrap_or(rest.len());
        let truncated: String = rest[..end].chars().take(200).collect();
        summary.push_str(&truncated);
    } else {
        let truncated: String = content_raw.chars().take(200).collect();
        summary.push_str(&truncated);
    }

    summary
}

// ---------------------------------------------------------------------------
// Consent loader — fetches CaptureConsent from FastAPI  (SPEC §7.3)
// ---------------------------------------------------------------------------

/// Fetch the current CaptureConsent from FastAPI /api/m1_1/consent.
/// Returns CaptureConsent::default() (Off) on any error so the daemon degrades safely.
pub async fn fetch_capture_consent(client: &reqwest::Client) -> CaptureConsent {
    #[derive(serde::Deserialize)]
    struct ConsentResponse {
        mode: String,
        #[serde(default)]
        allowed_processes: Vec<String>,
    }

    match client
        .get("http://127.0.0.1:8000/api/m1_1/consent")
        .send()
        .await
    {
        Ok(resp) if resp.status().is_success() => {
            match resp.json::<ConsentResponse>().await {
                Ok(body) => {
                    let mode = match body.mode.as_str() {
                        "all" => CaptureMode::AllApps,
                        "selected" => CaptureMode::SelectedApps,
                        _ => CaptureMode::Off,
                    };
                    CaptureConsent {
                        mode,
                        allowed_processes: body.allowed_processes,
                    }
                }
                Err(e) => {
                    eprintln!("[M1.1.1 WARN] consent parse error: {e}");
                    CaptureConsent::default()
                }
            }
        }
        Ok(resp) => {
            eprintln!("[M1.1.1 WARN] consent HTTP {}", resp.status());
            CaptureConsent::default()
        }
        Err(e) => {
            eprintln!("[M1.1.1 WARN] consent fetch failed (FastAPI unreachable?): {e}");
            CaptureConsent::default()
        }
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn truncate_chars(s: &str, max_chars: usize) -> String {
    s.chars().take(max_chars).collect()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::models::{AppBucket, CaptureConsent, CaptureMode};

    fn make_win(app: &str, title: Option<&str>) -> ForegroundWindow {
        ForegroundWindow {
            app_name: app.to_string(),
            app_bucket: crate::models::classify_process(app),
            window_title: title.map(|s| s.to_string()),
        }
    }

    #[test]
    fn test_process_window_off_discards_everything() {
        // AC-5: CaptureMode::Off → no window_title, no content_raw
        let win = make_win("Code.exe", Some("main.py - VSCode"));
        let consent = CaptureConsent::default();
        let capture = process_window(&win, &consent);
        assert!(capture.window_title.is_none());
        assert!(capture.content_raw.is_none());
        assert!(capture.content_summary.is_none());
    }

    #[test]
    fn test_process_window_selected_not_in_allowlist() {
        let win = make_win("notepad.exe", Some("Untitled - Notepad"));
        let consent = CaptureConsent {
            mode: CaptureMode::SelectedApps,
            allowed_processes: vec!["Code.exe".to_string()],
        };
        let capture = process_window(&win, &consent);
        assert!(capture.window_title.is_none());
        assert!(capture.content_raw.is_none());
    }

    #[test]
    fn test_process_window_selected_in_allowlist_gets_title() {
        // AllowList hit: window_title should be Some (content_raw None on non-Windows CI)
        let win = make_win("Code.exe", Some("main.py - VSCode"));
        let consent = CaptureConsent {
            mode: CaptureMode::SelectedApps,
            allowed_processes: vec!["Code.exe".to_string()],
        };
        let capture = process_window(&win, &consent);
        // window_title is preserved
        assert_eq!(capture.window_title.as_deref(), Some("main.py - VSCode"));
    }

    #[test]
    fn test_generate_summary_fallback_focus_block() {
        let raw = "[TITLE] main.py - VSCode\n[FOCUS] def hello():\n    pass\n[MAIN] ...";
        let summary = generate_content_summary_fallback(raw, "main.py - VSCode");
        assert!(summary.contains("main.py - VSCode"));
        assert!(summary.contains("def hello()"));
    }

    #[test]
    fn test_generate_summary_fallback_no_tags() {
        let raw = "Some plain text without any tags here";
        let summary = generate_content_summary_fallback(raw, "App Title");
        assert!(summary.starts_with("App Title"));
        assert!(summary.contains("Some plain text"));
    }

    #[test]
    fn test_truncate_chars_unicode_safe() {
        let s = "你好世界".repeat(1000);
        let truncated = truncate_chars(&s, 200);
        assert_eq!(truncated.chars().count(), 200);
    }
}
