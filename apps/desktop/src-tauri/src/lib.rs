use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

const DEFAULT_HOST: &str = "127.0.0.1";
const HEALTH_PATH: &str = "/health";
const STARTUP_TIMEOUT_SECS: u64 = 30;
const SIDECAR_NAME: &str = "persona-backend";

struct BackendChild(Mutex<Option<CommandChild>>);

fn append_log(file: &str, message: &str) {
    let Some(appdata) = std::env::var_os("APPDATA") else {
        return;
    };
    let mut dir = PathBuf::from(appdata);
    dir.push("PersonaAI");
    dir.push("logs");
    let _ = fs::create_dir_all(&dir);
    dir.push(file);
    if let Ok(mut handle) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(dir)
    {
        let _ = writeln!(handle, "{message}");
    }
}

fn pick_port() -> u16 {
    std::net::TcpListener::bind(format!("{DEFAULT_HOST}:0"))
        .expect("failed to bind ephemeral port")
        .local_addr()
        .expect("failed to read ephemeral port")
        .port()
}

fn wait_for_health(port: u16) -> Result<(), String> {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(2))
        .build()
        .map_err(|error| error.to_string())?;
    let url = format!("http://{DEFAULT_HOST}:{port}{HEALTH_PATH}");
    let deadline = Instant::now() + Duration::from_secs(STARTUP_TIMEOUT_SECS);

    while Instant::now() < deadline {
        if let Ok(response) = client.get(&url).send() {
            if response.status().is_success() {
                append_log("desktop.log", &format!("health ok {url}"));
                return Ok(());
            }
        }
        std::thread::sleep(Duration::from_millis(250));
    }

    Err(format!(
        "Backend did not respond at {url}. See %APPDATA%\\PersonaAI\\logs\\desktop.log and sidecar.log"
    ))
}

fn spawn_backend(app: &tauri::AppHandle, port: u16) -> Result<CommandChild, String> {
    append_log(
        "desktop.log",
        &format!("spawning {SIDECAR_NAME} on {DEFAULT_HOST}:{port}"),
    );

    let sidecar = app
        .shell()
        .sidecar(SIDECAR_NAME)
        .map_err(|error| {
            let msg = format!("sidecar missing ({SIDECAR_NAME}): {error}");
            append_log("desktop.log", &msg);
            msg
        })?
        .env("PERSONA_HOST", DEFAULT_HOST)
        .env("PERSONA_PORT", port.to_string());

    let (mut rx, child) = sidecar.spawn().map_err(|error| {
        let msg = format!("sidecar spawn denied or failed: {error}");
        append_log("desktop.log", &msg);
        msg
    })?;

    append_log("desktop.log", "sidecar process started");

    tauri::async_runtime::spawn(async move {
        while let Some(event) = rx.recv().await {
            match event {
                CommandEvent::Error(message) => {
                    append_log("desktop.log", &format!("sidecar error: {message}"));
                }
                CommandEvent::Stderr(line) => {
                    let text = String::from_utf8_lossy(&line);
                    append_log("sidecar.log", &format!("stderr: {text}"));
                }
                CommandEvent::Stdout(line) => {
                    let text = String::from_utf8_lossy(&line);
                    append_log("sidecar.log", &format!("stdout: {text}"));
                }
                CommandEvent::Terminated(payload) => {
                    append_log(
                        "desktop.log",
                        &format!("sidecar terminated: {payload:?}"),
                    );
                }
                _ => {}
            }
        }
    });

    Ok(child)
}

fn patch_ui(window: &tauri::WebviewWindow, status: &str, online: bool) {
    let script = format!(
        r#"(function() {{
  var el = document.getElementById("backendStatus");
  if (el) el.textContent = {status:?};
  var pill = document.getElementById("healthPill");
  if (pill) {{
    pill.textContent = {online:?};
    pill.classList.remove("pill-ok", "pill-warn", "pill-muted");
    pill.classList.add({online:?} === "Online" ? "pill-ok" : "pill-warn");
  }}
}})();"#,
        status = status,
        online = if online { "Online" } else { "Offline" },
    );
    let _ = window.eval(&script);
}

fn inject_backend_ready(window: &tauri::WebviewWindow, port: u16) {
    let api_base = format!("http://{DEFAULT_HOST}:{port}");
    append_log("desktop.log", &format!("backend ready at {api_base}"));
    let script = format!(
        r#"if (window.__personaSetApiBase) window.__personaSetApiBase({api_base:?});"#
    );
    let _ = window.eval(&script);
}

fn show_startup_error(window: &tauri::WebviewWindow, message: &str) {
    append_log("desktop.log", &format!("startup error: {message}"));
    patch_ui(window, message, false);
    let script = format!(
        r#"if (window.__personaStartupFailed) window.__personaStartupFailed({message:?});"#
    );
    let _ = window.eval(&script);
}

fn mark_desktop_shell(window: &tauri::WebviewWindow) {
    let _ = window.eval("window.__PERSONA_DESKTOP__ = true;");
}

fn start_backend_async(app: tauri::AppHandle) {
    std::thread::spawn(move || {
        let window = match app.get_webview_window("main") {
            Some(w) => w,
            None => {
                append_log("desktop.log", "main window missing");
                return;
            }
        };

        let outcome: Result<u16, String> = (|| {
            let port = pick_port();
            let child = spawn_backend(&app, port)?;
            {
                let state = app.state::<BackendChild>();
                let mut guard = state.0.lock().expect("backend child lock");
                *guard = Some(child);
            }
            wait_for_health(port)?;
            Ok(port)
        })();

        let _ = app.run_on_main_thread(move || match outcome {
            Ok(port) => inject_backend_ready(&window, port),
            Err(message) => show_startup_error(&window, &message),
        });
    });
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    append_log("desktop.log", "Persona AI desktop starting");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(BackendChild(Mutex::new(None)))
        .setup(|app| {
            let window = if let Some(existing) = app.get_webview_window("main") {
                existing
            } else {
                WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
                    .title("Persona AI")
                    .inner_size(1180.0, 820.0)
                    .min_inner_size(900.0, 640.0)
                    .build()
                    .map_err(|error| error.to_string())?
            };

            mark_desktop_shell(&window);
            start_backend_async(app.handle().clone());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            if matches!(event, RunEvent::Exit) {
                if let Some(state) = app.try_state::<BackendChild>() {
                    if let Ok(mut guard) = state.0.lock() {
                        if let Some(child) = guard.take() {
                            let _ = child.kill();
                        }
                    }
                }
            }
        });
}
