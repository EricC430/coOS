mod commands;
mod sidecar;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|_app| {
            // FastAPI sidecar は Phase 0 では手動起動。Phase 1 以降で自動化。
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_system_health,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
