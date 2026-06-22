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

#[derive(Clone)]
pub struct InputDebouncer {
    wpm_calc: Arc<Mutex<WpmCalculator>>,
    key_count_window: Arc<Mutex<u32>>,
    scroll_count_window: Arc<Mutex<u32>>,
    is_foreground_active: Arc<Mutex<bool>>,
}

impl InputDebouncer {
    pub fn new() -> Self {
        Self {
            wpm_calc: Arc::new(Mutex::new(WpmCalculator::new())),
            key_count_window: Arc::new(Mutex::new(0)),
            scroll_count_window: Arc::new(Mutex::new(0)),
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

    /// Called on each Raw Input mouse scroll event.
    /// Only accumulates when foreground is active.
    pub fn on_scroll_event(&self) {
        if !*self.is_foreground_active.lock().unwrap() {
            return;
        }
        *self.scroll_count_window.lock().unwrap() += 1;
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

    pub fn drain_scroll_count(&self) -> u32 {
        let mut count = self.scroll_count_window.lock().unwrap();
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

#[cfg(windows)]
pub fn spawn_raw_input_listener(debouncer: InputDebouncer) {
    use std::thread;
    use windows::core::w;
    use windows::Win32::Foundation::{HWND, LPARAM, LRESULT, WPARAM};
    use windows::Win32::UI::WindowsAndMessaging::{
        CreateWindowExW, DefWindowProcW, RegisterClassW, GetMessageW, TranslateMessage,
        DispatchMessageW, WNDCLASSW, MSG, WS_EX_TOOLWINDOW, WS_OVERLAPPED, GWLP_USERDATA,
        SetWindowLongPtrW, GetWindowLongPtrW, WM_CREATE, WM_INPUT, CREATESTRUCTW,
        CS_HREDRAW, CS_VREDRAW, WM_KEYDOWN, WM_SYSKEYDOWN,
    };
    use windows::Win32::UI::Input::{
        RAWINPUTDEVICE, RegisterRawInputDevices, RIDEV_INPUTSINK,
        GetRawInputData, HRAWINPUT, RAWINPUT, RAWINPUTHEADER, RID_INPUT, RIM_TYPEKEYBOARD,
        RIM_TYPEMOUSE,
    };

    struct WindowState {
        debouncer: InputDebouncer,
    }

    unsafe extern "system" fn window_proc(
        hwnd: HWND,
        msg: u32,
        wparam: WPARAM,
        lparam: LPARAM,
    ) -> LRESULT {
        if msg == WM_CREATE {
            let create_struct = lparam.0 as *const CREATESTRUCTW;
            if !create_struct.is_null() {
                let state_ptr = (*create_struct).lpCreateParams;
                SetWindowLongPtrW(hwnd, GWLP_USERDATA, state_ptr as isize);
            }
        }

        let state_ptr = GetWindowLongPtrW(hwnd, GWLP_USERDATA) as *const WindowState;
        if !state_ptr.is_null() {
            let state = &*state_ptr;
            if msg == WM_INPUT {
                let hrawinput = HRAWINPUT(lparam.0 as *mut std::ffi::c_void);
                let mut size: u32 = 0;
                
                let res = GetRawInputData(
                    hrawinput,
                    RID_INPUT,
                    None,
                    &mut size,
                    std::mem::size_of::<RAWINPUTHEADER>() as u32,
                );
                
                if res != u32::MAX && size > 0 {
                    let mut buffer = vec![0u8; size as usize];
                    let res = GetRawInputData(
                        hrawinput,
                        RID_INPUT,
                        Some(buffer.as_mut_ptr() as *mut std::ffi::c_void),
                        &mut size,
                        std::mem::size_of::<RAWINPUTHEADER>() as u32,
                    );
                    
                    if res != u32::MAX {
                        let raw = &*(buffer.as_ptr() as *const RAWINPUT);
                        if raw.header.dwType == RIM_TYPEKEYBOARD.0 {
                            let keyboard = &raw.data.keyboard;
                            let msg = keyboard.Message;
                            if msg == WM_KEYDOWN || msg == WM_SYSKEYDOWN {
                                state.debouncer.on_key_event(1);
                            }
                        } else if raw.header.dwType == RIM_TYPEMOUSE.0 {
                            let mouse = &raw.data.mouse;
                            if (mouse.Anonymous.Anonymous.usButtonFlags & 0x0400) != 0 { // 0x0400 is RI_MOUSE_WHEEL
                                state.debouncer.on_scroll_event();
                            }
                        }
                    }
                }
            }
        }

        DefWindowProcW(hwnd, msg, wparam, lparam)
    }

    thread::spawn(move || unsafe {
        let class_name = w!("RawInputHiddenWindow");
        
        let wnd_class = WNDCLASSW {
            style: CS_HREDRAW | CS_VREDRAW,
            lpfnWndProc: Some(window_proc),
            lpszClassName: class_name,
            ..Default::default()
        };
        
        let atom = RegisterClassW(&wnd_class);
        if atom == 0 {
            eprintln!("[M1.1.2 ERROR] RegisterClassW failed");
            return;
        }

        let state = Box::new(WindowState { debouncer });
        let state_ptr = Box::into_raw(state);

        let hwnd = match CreateWindowExW(
            WS_EX_TOOLWINDOW,
            class_name,
            w!("RawInputListener"),
            WS_OVERLAPPED,
            0,
            0,
            0,
            0,
            HWND::default(),
            None,
            None,
            Some(state_ptr as *const std::ffi::c_void),
        ) {
            Ok(h) => h,
            Err(e) => {
                eprintln!("[M1.1.2 ERROR] CreateWindowExW failed: {:?}", e);
                let _ = Box::from_raw(state_ptr);
                return;
            }
        };

        // Register both Keyboard (Usage Page 1, Usage 6) and Mouse (Usage Page 1, Usage 2)
        let devices = [
            RAWINPUTDEVICE {
                usUsagePage: 1,
                usUsage: 6, // Keyboard
                dwFlags: RIDEV_INPUTSINK,
                hwndTarget: hwnd,
            },
            RAWINPUTDEVICE {
                usUsagePage: 1,
                usUsage: 2, // Mouse
                dwFlags: RIDEV_INPUTSINK,
                hwndTarget: hwnd,
            },
        ];

        if let Err(e) = RegisterRawInputDevices(&devices, std::mem::size_of::<RAWINPUTDEVICE>() as u32) {
            eprintln!("[M1.1.2 ERROR] RegisterRawInputDevices failed: {:?}", e);
            let _ = Box::from_raw(state_ptr);
            return;
        }

        eprintln!("[M1.1.2 INFO] Raw Input keyboard and mouse hooks registered successfully");

        let mut msg = MSG::default();
        while GetMessageW(&mut msg, HWND::default(), 0, 0).0 != 0 {
            let _ = TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }

        let _ = Box::from_raw(state_ptr);
    });
}


#[cfg(not(windows))]
pub fn spawn_raw_input_listener(_debouncer: InputDebouncer) {
    // Non-Windows stub
}
