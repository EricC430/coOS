/// M1.1 HTTP emitter — POSTs TelemetryEvents to FastAPI /api/m1_1/event
///
/// SPEC: docs/modules/M1_1_os_telemetry_daemon_SPEC.md §4 (downstream M0.4)
/// All events go through this single path so tests can intercept at the HTTP layer.
use crate::models::TelemetryEvent;

const FASTAPI_ENDPOINT: &str = "http://127.0.0.1:8000/api/m1_1/event";

pub struct Emitter {
    client: reqwest::Client,
    endpoint: String,
}

impl Emitter {
    pub fn new() -> Self {
        Self {
            client: reqwest::Client::new(),
            endpoint: FASTAPI_ENDPOINT.to_string(),
        }
    }

    pub async fn emit(&self, event: TelemetryEvent) {
        // Fire-and-forget: log failure but never block the main polling loop
        match self.client.post(&self.endpoint).json(&event).send().await {
            Ok(resp) if resp.status().is_success() => {}
            Ok(resp) => {
                eprintln!("[M1.1] emit HTTP {}: {:?}", resp.status(), event.action);
            }
            Err(e) => {
                eprintln!("[M1.1] emit error (FastAPI unreachable?): {e}");
            }
        }
    }
}

impl Default for Emitter {
    fn default() -> Self {
        Self::new()
    }
}
