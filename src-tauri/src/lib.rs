use std::sync::{Arc, Mutex};
use std::time::Duration;
use rand::RngCore;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BackendConnection {
    pub host: String,
    pub port: u16,
    pub token: String,
    pub pid: Option<u32>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct DesktopInfo {
    pub app_version: String,
    pub platform: String,
    pub arch: String,
}

pub struct AppState {
    pub connection: Mutex<Option<BackendConnection>>,
    pub child: Mutex<Option<CommandChild>>,
}

fn generate_launch_token() -> String {
    let mut bytes = [0u8; 32];
    rand::thread_rng().fill_bytes(&mut bytes);
    bytes.iter().map(|b| format!("{:02x}", b)).collect()
}

#[tauri::command]
fn get_backend_connection(state: tauri::State<'_, Arc<AppState>>) -> Result<BackendConnection, String> {
    let guard = state.connection.lock().map_err(|e| e.to_string())?;
    guard
        .clone()
        .ok_or_else(|| "ATEval backend sidecar is still initializing...".to_string())
}

#[tauri::command]
fn get_desktop_info() -> DesktopInfo {
    DesktopInfo {
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        platform: std::env::consts::OS.to_string(),
        arch: std::env::consts::ARCH.to_string(),
    }
}

async fn spawn_and_handshake_sidecar(
    app: AppHandle,
    state: Arc<AppState>,
    token: String,
) -> Result<BackendConnection, String> {
    // Check if an existing external backend was configured via environment
    if let (Ok(port_str), Ok(tok)) = (std::env::var("ATEVAL_API_PORT"), std::env::var("ATEVAL_LAUNCH_TOKEN")) {
        if let Ok(port) = port_str.parse::<u16>() {
            let conn = BackendConnection {
                host: "127.0.0.1".to_string(),
                port,
                token: tok,
                pid: None,
            };
            let mut guard = state.connection.lock().unwrap();
            *guard = Some(conn.clone());
            return Ok(conn);
        }
    }

    println!("[ateval-desktop] Spawning ateval-api sidecar with dynamic port on 127.0.0.1...");
    let sidecar_cmd = app
        .shell()
        .sidecar("ateval-api")
        .map_err(|e| format!("Failed to configure ateval-api sidecar: {}", e))?
        .args(["--port", "0"])
        .env("ATEVAL_LAUNCH_TOKEN", &token);

    let (mut rx, child) = sidecar_cmd
        .spawn()
        .map_err(|e| format!("Failed to spawn ateval-api sidecar: {}", e))?;

    // Store child handle for lifecycle cleanup
    {
        let mut child_guard = state.child.lock().unwrap();
        *child_guard = Some(child);
    }

    let mut detected_port: Option<u16> = None;
    let mut detected_pid: Option<u32> = None;

    // Timeout handshake at 30 seconds
    let handshake_deadline = tokio::time::sleep(Duration::from_secs(30));
    tokio::pin!(handshake_deadline);

    loop {
        tokio::select! {
            _ = &mut handshake_deadline => {
                return Err("Timeout waiting for ateval-api sidecar readiness handshake (30s elapsed)".to_string());
            }
            event_opt = rx.recv() => {
                match event_opt {
                    Some(CommandEvent::Stdout(bytes)) => {
                        let text = String::from_utf8_lossy(&bytes);
                        for line in text.lines() {
                            let trimmed = line.trim();
                            if trimmed.starts_with('{') && trimmed.ends_with('}') {
                                if let Ok(val) = serde_json::from_str::<serde_json::Value>(trimmed) {
                                    if val.get("event").and_then(|v| v.as_str()) == Some("ready") {
                                        if let Some(port) = val.get("port").and_then(|p| p.as_u64()) {
                                            detected_port = Some(port as u16);
                                            detected_pid = val.get("pid").and_then(|p| p.as_u64()).map(|p| p as u32);
                                            break;
                                        }
                                    }
                                }
                            }
                            println!("[sidecar stdout] {}", trimmed);
                        }
                        if detected_port.is_some() {
                            break;
                        }
                    }
                    Some(CommandEvent::Stderr(bytes)) => {
                        eprintln!("[sidecar stderr] {}", String::from_utf8_lossy(&bytes).trim());
                    }
                    Some(CommandEvent::Error(err)) => {
                        return Err(format!("Sidecar runtime error: {}", err));
                    }
                    Some(CommandEvent::Terminated(payload)) => {
                        return Err(format!("Sidecar terminated prematurely with code {:?}", payload.code));
                    }
                    None => {
                        return Err("Sidecar stream closed unexpectedly without readiness event".to_string());
                    }
                }
            }
        }
    }

    let port = detected_port.ok_or_else(|| "Failed to parse sidecar port from handshake".to_string())?;
    println!("[ateval-desktop] Sidecar successfully ready at 127.0.0.1:{} (pid {:?})", port, detected_pid);

    let conn = BackendConnection {
        host: "127.0.0.1".to_string(),
        port,
        token,
        pid: detected_pid,
    };

    {
        let mut guard = state.connection.lock().unwrap();
        *guard = Some(conn.clone());
    }

    // Continue background reader to drain stdout/stderr and prevent pipe buffering stalls
    tokio::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Stdout(bytes) => {
                    let s = String::from_utf8_lossy(&bytes);
                    print!("[sidecar] {}", s);
                }
                CommandEvent::Stderr(bytes) => {
                    let s = String::from_utf8_lossy(&bytes);
                    eprint!("[sidecar err] {}", s);
                }
                CommandEvent::Terminated(status) => {
                    eprintln!("[sidecar] Process exited with {:?}", status.code);
                    break;
                }
                _ => {}
            }
        }
    });

    Ok(conn)
}

pub fn run() {
    let token = generate_launch_token();
    let state = Arc::new(AppState {
        connection: Mutex::new(None),
        child: Mutex::new(None),
    });

    let app_state_for_setup = Arc::clone(&state);
    let app_state_for_cleanup = Arc::clone(&state);

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(Arc::clone(&state))
        .invoke_handler(tauri::generate_handler![
            get_backend_connection,
            get_desktop_info,
        ])
        .setup(move |app| {
            let app_handle = app.handle().clone();
            let state_clone = Arc::clone(&app_state_for_setup);
            let launch_token = token.clone();

            // Set native application menu on macOS
            #[cfg(target_os = "macos")]
            {
                if let Ok(menu) = tauri::menu::Menu::default(&app_handle) {
                    let _ = app.set_menu(menu);
                }
            }

            // Spawn sidecar asynchronously in tokio runtime
            tauri::async_runtime::spawn(async move {
                if let Err(e) = spawn_and_handshake_sidecar(app_handle, state_clone, launch_token).await {
                    eprintln!("[ateval-desktop] FATAL: Sidecar startup failed: {}", e);
                }
            });

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    app.run(move |_app_handle, event| {
        if let RunEvent::Exit = event {
            println!("[ateval-desktop] Application exiting: shutting down sidecar child process...");
            let mut guard = app_state_for_cleanup.child.lock().unwrap();
            if let Some(child) = guard.take() {
                let _ = child.kill();
            }
        }
    });
}
