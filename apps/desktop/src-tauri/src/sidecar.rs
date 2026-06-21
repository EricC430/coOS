use std::process::{Command, Child};
use std::thread;
use std::sync::Mutex;

static DAEMON_CHILD: Mutex<Option<Child>> = Mutex::new(None);

pub fn spawn_telemetry_daemon() {
    thread::spawn(|| {
        #[cfg(debug_assertions)]
        {
            println!("[Tauri] Spawning telemetry daemon in dev mode via cargo...");
            let mut cmd = Command::new("cargo");
            cmd.args(&["run", "-p", "m1_1_telemetry_daemon"]);

            #[cfg(windows)]
            {
                use std::os::windows::process::CommandExt;
                const CREATE_NO_WINDOW: u32 = 0x08000000;
                cmd.creation_flags(CREATE_NO_WINDOW);
            }

            match cmd.spawn() {
                Ok(child) => {
                    println!("[Tauri] Telemetry daemon spawned successfully (PID: {})", child.id());
                    if let Ok(mut guard) = DAEMON_CHILD.lock() {
                        *guard = Some(child);
                    }
                }
                Err(e) => {
                    eprintln!("[Tauri] Failed to spawn telemetry daemon: {}", e);
                }
            }
        }
    });
}

pub fn kill_telemetry_daemon() {
    if let Ok(mut guard) = DAEMON_CHILD.lock() {
        if let Some(mut child) = guard.take() {
            println!("[Tauri] Terminating telemetry daemon process...");
            let _ = child.kill();
        }
    }
}

pub fn _spawn_sidecar() {
    // TODO(M0.2): implement auto-spawn with OS job object / process group binding
}
