mod commands;
mod sidecar;
mod socket_server;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_dialog::init())
        .setup(|_app| {
            // Start the local socket server for telemetry
            tauri::async_runtime::spawn(socket_server::start_socket_server());

            // Automatically start the telemetry daemon sidecar
            sidecar::spawn_telemetry_daemon();

            // FastAPI sidecar は Phase 0 では手動起動。Phase 1 以降で自動化。
            Ok(())
        })

        .invoke_handler(tauri::generate_handler![
            commands::get_system_health,
        ])
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(|_app_handle, event| {
        if let tauri::RunEvent::Exit = event {
            sidecar::kill_telemetry_daemon();
        }
    });
}
