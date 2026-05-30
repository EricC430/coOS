use serde_json::{json, Value};

#[tauri::command]
pub async fn get_system_health() -> Result<Value, String> {
    let sidecar_ok = check_sidecar_health().await;
    Ok(json!({
        "status": "ok",
        "sidecar_reachable": sidecar_ok,
    }))
}

async fn check_sidecar_health() -> bool {
    reqwest::get("http://127.0.0.1:8000/api/health")
        .await
        .map(|r| r.status().is_success())
        .unwrap_or(false)
}
