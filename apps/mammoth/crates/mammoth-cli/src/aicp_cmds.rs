/// AICP feature-parity commands for the Mammoth CLI.
///
/// These commands delegate to:
/// - The AICP runtime HTTP API (for live-runtime queries: caps, run, appr, logs)
/// - The `aicp` Python CLI (for workspace operations: scan, dev, policy, map, test)
///
/// The AICP server URL is resolved from:
///   1. `AICP_URL` environment variable
///   2. Default: `http://localhost:8000`
use std::io::{self, Write};
use std::process::Command;

/// Default AICP runtime base URL.
pub const DEFAULT_AICP_URL: &str = "http://localhost:8000";

/// Resolve the AICP runtime URL from environment or default.
pub fn aicp_url() -> String {
    std::env::var("AICP_URL").unwrap_or_else(|_| DEFAULT_AICP_URL.to_string())
}

// ---------------------------------------------------------------------------
// HTTP helpers (curl-based, no extra deps)
// ---------------------------------------------------------------------------

/// Run a curl GET and return the body as a String.
fn curl_get(path: &str) -> Result<String, String> {
    let url = format!("{}{path}", aicp_url());
    let out = Command::new("curl")
        .args(["-sf", "--max-time", "10", &url])
        .output()
        .map_err(|e| format!("curl not found: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "GET {url} failed ({}): {}",
            out.status,
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    Ok(String::from_utf8_lossy(&out.stdout).into_owned())
}

/// Run a curl POST with a JSON body and return the response body.
fn curl_post(path: &str, body: &str) -> Result<String, String> {
    let url = format!("{}{path}", aicp_url());
    let out = Command::new("curl")
        .args([
            "-sf",
            "--max-time",
            "30",
            "-X",
            "POST",
            "-H",
            "Content-Type: application/json",
            "-d",
            body,
            &url,
        ])
        .output()
        .map_err(|e| format!("curl not found: {e}"))?;
    if !out.status.success() {
        return Err(format!(
            "POST {url} failed ({}): {}",
            out.status,
            String::from_utf8_lossy(&out.stderr)
        ));
    }
    Ok(String::from_utf8_lossy(&out.stdout).into_owned())
}

// ---------------------------------------------------------------------------
// aicp delegation helper
// ---------------------------------------------------------------------------

/// Delegate to the `aicp` Python CLI. Streams stdout/stderr directly.
fn delegate_aicp(args: &[&str]) -> Result<(), String> {
    let status = Command::new("aicp")
        .args(args)
        .status()
        .map_err(|e| format!("`aicp` CLI not found. Is it installed? ({e})"))?;
    if !status.success() {
        return Err(format!("`aicp {}` exited with {status}", args.join(" ")));
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// caps / ls — list registered capabilities
// ---------------------------------------------------------------------------

/// `mammoth caps [--json]` — list capabilities registered on the AICP runtime.
pub fn run_caps(json: bool) -> Result<(), String> {
    let body = curl_get("/discover")?;
    if json {
        println!("{body}");
        return Ok(());
    }
    // Pretty-print the capabilities array.
    match serde_json::from_str::<serde_json::Value>(&body) {
        Ok(val) => {
            let caps = val
                .get("capabilities")
                .or_else(|| val.as_array().map(|_| &val))
                .and_then(|v| v.as_array())
                .cloned()
                .unwrap_or_default();
            if caps.is_empty() {
                println!(
                    "No capabilities registered (is the AICP runtime running at {}?)",
                    aicp_url()
                );
                return Ok(());
            }
            println!("Capabilities ({} total)  [{}]", caps.len(), aicp_url());
            println!("{:<40} {:<10} Description", "Name", "Kind");
            println!("{}", "-".repeat(80));
            for cap in &caps {
                let name = cap.get("name").and_then(|v| v.as_str()).unwrap_or("-");
                let kind = cap.get("kind").and_then(|v| v.as_str()).unwrap_or("-");
                let desc = cap
                    .get("description")
                    .and_then(|v| v.as_str())
                    .unwrap_or("-");
                println!("{name:<40} {kind:<10} {desc}");
            }
        }
        Err(_) => {
            // Fallback: dump raw body
            println!("{body}");
        }
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// run — execute a capability
// ---------------------------------------------------------------------------

/// `mammoth run <capability_name> [--input '{"key":"value"}'] [--json]`
///
/// Executes the named capability via POST /execute/<name>.
pub fn run_capability(
    capability: &str,
    input_json: Option<&str>,
    json: bool,
) -> Result<(), String> {
    let body = input_json.unwrap_or("{}");
    let path = format!("/execute/{capability}");
    let response = curl_post(&path, body)?;
    if json {
        println!("{response}");
        return Ok(());
    }
    match serde_json::from_str::<serde_json::Value>(&response) {
        Ok(val) => {
            let status = val
                .get("status")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            let exec_id = val
                .get("execution_id")
                .and_then(|v| v.as_str())
                .unwrap_or("-");
            let rendered = val.get("rendered").and_then(|v| v.as_str());
            println!("Execution  {exec_id}");
            println!("Status     {status}");
            if let Some(data) = val.get("data") {
                println!(
                    "Data       {}",
                    serde_json::to_string_pretty(data).unwrap_or_default()
                );
            }
            if let Some(r) = rendered {
                println!("Rendered   {r}");
            }
            if let Some(err) = val.get("error").and_then(|v| v.as_str()) {
                println!("Error      {err}");
            }
        }
        Err(_) => println!("{response}"),
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// appr — approval management
// ---------------------------------------------------------------------------

/// `mammoth appr ls [--json]` — list pending approvals.
pub fn run_appr_ls(json: bool) -> Result<(), String> {
    let body = curl_get("/approvals")?;
    if json {
        println!("{body}");
        return Ok(());
    }
    match serde_json::from_str::<serde_json::Value>(&body) {
        Ok(val) => {
            let items = val.as_array().cloned().unwrap_or_default();
            if items.is_empty() {
                println!("No pending approvals.");
                return Ok(());
            }
            println!("Pending approvals ({})", items.len());
            println!("{:<36} {:<30} Status", "ID", "Capability");
            println!("{}", "-".repeat(80));
            for item in &items {
                let id = item
                    .get("approval_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("-");
                let cap = item
                    .get("capability_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("-");
                let status = item.get("status").and_then(|v| v.as_str()).unwrap_or("-");
                println!("{id:<36} {cap:<30} {status}");
            }
        }
        Err(_) => println!("{body}"),
    }
    Ok(())
}

/// `mammoth appr decide <id> <approve|deny> [--reason TEXT]`
pub fn run_appr_decide(
    approval_id: &str,
    decision: &str,
    reason: Option<&str>,
) -> Result<(), String> {
    let effect = match decision.to_lowercase().as_str() {
        "approve" | "allow" | "yes" => "approve",
        "deny" | "reject" | "no" => "deny",
        other => return Err(format!("unknown decision '{other}' — use approve or deny")),
    };
    let body = serde_json::json!({
        "decision": effect,
        "reason": reason.unwrap_or("")
    })
    .to_string();
    let path = format!("/approvals/{approval_id}/decide");
    let response = curl_post(&path, &body)?;
    match serde_json::from_str::<serde_json::Value>(&response) {
        Ok(val) => {
            let status = val
                .get("status")
                .and_then(|v| v.as_str())
                .unwrap_or("unknown");
            println!("Approval {approval_id} → {status}");
        }
        Err(_) => println!("{response}"),
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// logs — execution history
// ---------------------------------------------------------------------------

/// `mammoth logs [--limit N] [--json]` — show recent execution history.
pub fn run_logs(limit: usize, json: bool) -> Result<(), String> {
    let body = curl_get("/history")?;
    if json {
        println!("{body}");
        return Ok(());
    }
    match serde_json::from_str::<serde_json::Value>(&body) {
        Ok(val) => {
            let mut items = val.as_array().cloned().unwrap_or_default();
            items.truncate(limit);
            if items.is_empty() {
                println!("No executions recorded.");
                return Ok(());
            }
            println!(
                "{:<36} {:<30} {:<10} Time",
                "Execution ID", "Capability", "Status"
            );
            println!("{}", "-".repeat(90));
            for item in &items {
                let id = item
                    .get("execution_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("-");
                let cap = item
                    .get("capability_name")
                    .and_then(|v| v.as_str())
                    .unwrap_or("-");
                let status = item.get("status").and_then(|v| v.as_str()).unwrap_or("-");
                let ts = item
                    .get("timestamp")
                    .and_then(|v| v.as_str())
                    .unwrap_or("-");
                println!("{id:<36} {cap:<30} {status:<10} {ts}");
            }
        }
        Err(_) => println!("{body}"),
    }
    Ok(())
}

// ---------------------------------------------------------------------------
// scan — delegate to `aicp scan`
// ---------------------------------------------------------------------------

/// `mammoth scan [PATH] [--framework FRAMEWORK]`
pub fn run_scan(path: Option<&str>, framework: Option<&str>) -> Result<(), String> {
    let mut args: Vec<&str> = vec!["scan"];
    if let Some(p) = path {
        args.push(p);
    }
    if let Some(f) = framework {
        args.extend_from_slice(&["--framework", f]);
    }
    delegate_aicp(&args)
}

// ---------------------------------------------------------------------------
// dev — delegate to `aicp dev`
// ---------------------------------------------------------------------------

/// `mammoth dev [PATH] [--port PORT]`
pub fn run_dev(path: Option<&str>, port: Option<&str>) -> Result<(), String> {
    let mut args: Vec<&str> = vec!["dev"];
    if let Some(p) = path {
        args.push(p);
    }
    if let Some(port) = port {
        args.extend_from_slice(&["--port", port]);
    }
    delegate_aicp(&args)
}

// ---------------------------------------------------------------------------
// policy — delegate to `aicp policy <subcommand>`
// ---------------------------------------------------------------------------

/// `mammoth policy <safe|ask|deny|approve|protect|limit> [CAPABILITY] [ARGS...]`
pub fn run_policy(subcmd: &str, rest: &[String]) -> Result<(), String> {
    let mut args: Vec<&str> = vec!["policy", subcmd];
    for r in rest {
        args.push(r.as_str());
    }
    delegate_aicp(&args)
}

// ---------------------------------------------------------------------------
// map — delegate to `aicp map <format>`
// ---------------------------------------------------------------------------

/// `mammoth map <openapi|curl|har|postman> [FILE]`
pub fn run_map(format: &str, file: Option<&str>) -> Result<(), String> {
    let mut args = vec!["map", format];
    if let Some(f) = file {
        args.push(f);
    }
    delegate_aicp(&args)
}

// ---------------------------------------------------------------------------
// test — delegate to `aicp test`
// ---------------------------------------------------------------------------

/// `mammoth test [CAPABILITY] [--verbose]`
pub fn run_test(capability: Option<&str>, verbose: bool) -> Result<(), String> {
    let mut args: Vec<&str> = vec!["test"];
    if let Some(c) = capability {
        args.push(c);
    }
    if verbose {
        args.push("--verbose");
    }
    delegate_aicp(&args)
}

// ---------------------------------------------------------------------------
// status — quick health check
// ---------------------------------------------------------------------------

/// `mammoth status` — show AICP runtime health.
pub fn run_status_check() -> Result<(), String> {
    let url = format!("{}/providers/health", aicp_url());
    let out = Command::new("curl")
        .args(["-sf", "--max-time", "5", &url])
        .output()
        .map_err(|e| format!("curl not found: {e}"))?;
    if out.status.success() {
        let body = String::from_utf8_lossy(&out.stdout);
        let stdout = io::stdout();
        let mut lock = stdout.lock();
        writeln!(lock, "AICP runtime is reachable at {}", aicp_url()).ok();
        writeln!(lock, "{body}").ok();
    } else {
        let stderr = String::from_utf8_lossy(&out.stderr);
        eprintln!("AICP runtime not reachable at {} — {stderr}", aicp_url());
        eprintln!("Start it with: aicp dev  OR  aicp serve");
    }
    Ok(())
}
