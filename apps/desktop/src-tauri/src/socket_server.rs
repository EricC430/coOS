use tokio::io::{AsyncBufReadExt, BufReader};
use reqwest::Client;

#[cfg(unix)]
use std::env;
#[cfg(unix)]
use tokio::net::UnixListener;
#[cfg(windows)]
use tokio::net::windows::named_pipe::ServerOptions;

pub async fn start_socket_server() {
    let client = Client::new();
    
    #[cfg(windows)]
    {
        let pipe_name = r"\\.\pipe\coos_telemetry";
        loop {
            let server = match ServerOptions::new()
                .first_pipe_instance(false)
                .create(pipe_name) {
                    Ok(s) => s,
                    Err(e) => {
                        eprintln!("Failed to create named pipe: {}", e);
                        tokio::time::sleep(tokio::time::Duration::from_secs(1)).await;
                        continue;
                    }
                };

            if server.connect().await.is_ok() {
                let client_clone = client.clone();
                tokio::spawn(async move {
                    let mut lines = BufReader::new(server).lines();
                    while let Ok(Some(line)) = lines.next_line().await {
                        let _ = client_clone.post("http://127.0.0.1:8000/api/m1_1/event")
                            .body(line)
                            .header("Content-Type", "application/json")
                            .send()
                            .await;
                    }
                });
            }
        }
    }

    #[cfg(unix)]
    {
        let socket_path = env::temp_dir().join("coos_telemetry.sock");
        if socket_path.exists() {
            let _ = std::fs::remove_file(&socket_path);
        }
        
        let listener = match UnixListener::bind(&socket_path) {
            Ok(l) => l,
            Err(e) => {
                eprintln!("Failed to bind unix socket: {}", e);
                return;
            }
        };

        loop {
            if let Ok((stream, _)) = listener.accept().await {
                let client_clone = client.clone();
                tokio::spawn(async move {
                    let mut lines = BufReader::new(stream).lines();
                    while let Ok(Some(line)) = lines.next_line().await {
                        let _ = client_clone.post("http://127.0.0.1:8000/api/m1_1/event")
                            .body(line)
                            .header("Content-Type", "application/json")
                            .send()
                            .await;
                    }
                });
            }
        }
    }
}
