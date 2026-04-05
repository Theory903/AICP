use aicp::{AicpClient, ExecutionEnvelope};
use mammoth_runtime::AicpConfig;
use std::io::{self, Write};
use std::process::Command;

fn build_client() -> AicpClient {
    AicpClient::new(&AicpConfig::default())
}

fn runtime_url() -> String {
    AicpConfig::default().resolve_url()
}

fn build_runtime() -> Result<tokio::runtime::Runtime, String> {
    tokio::runtime::Runtime::new().map_err(|error| error.to_string())
}

fn render_json(value: &serde_json::Value) -> String {
    serde_json::to_string_pretty(value).unwrap_or_else(|_| value.to_string())
}

fn print_execution(envelope: &ExecutionEnvelope) {
    let status = envelope.status.as_deref().unwrap_or("unknown");
    let exec_id = envelope.execution_id.as_deref().unwrap_or("-");
    println!("Execution  {exec_id}");
    println!("Status     {status}");
    if let Some(data) = &envelope.data {
        println!("Data       {}", render_json(data));
    }
    if let Some(rendered) = &envelope.rendered {
        println!("Rendered   {rendered}");
    }
    if let Some(error) = &envelope.error {
        println!("Error      {error}");
    }
}

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

pub fn run_caps(json: bool) -> Result<(), String> {
    let rt = build_runtime()?;
    let client = build_client();
    let caps = rt
        .block_on(client.list_capabilities())
        .map_err(|e| e.to_string())?;

    if json {
        let body = serde_json::Value::Array(caps.clone());
        println!("{}", render_json(&body));
        return Ok(());
    }

    if caps.is_empty() {
        println!(
            "No capabilities registered (is the AICP runtime running at {}?)",
            runtime_url()
        );
        return Ok(());
    }

    println!("Capabilities ({} total)  [{}]", caps.len(), runtime_url());
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

    Ok(())
}

pub fn run_capability(
    capability: &str,
    input_json: Option<&str>,
    json: bool,
) -> Result<(), String> {
    let rt = build_runtime()?;
    let client = build_client();
    let body = input_json.unwrap_or("{}");
    let response = rt
        .block_on(client.execute(capability, body))
        .map_err(|e| e.to_string())?;

    if json {
        let value = serde_json::to_value(&response).map_err(|e| e.to_string())?;
        println!("{}", render_json(&value));
        return Ok(());
    }

    print_execution(&response);
    Ok(())
}

pub fn run_appr_ls(json: bool) -> Result<(), String> {
    let rt = build_runtime()?;
    let client = build_client();
    let items = rt
        .block_on(client.list_approvals())
        .map_err(|e| e.to_string())?;

    if json {
        let body = serde_json::Value::Array(items.clone());
        println!("{}", render_json(&body));
        return Ok(());
    }

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

    Ok(())
}

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

    let rt = build_runtime()?;
    let client = build_client();
    let response = rt
        .block_on(client.decide_approval(approval_id, effect, reason.unwrap_or("")))
        .map_err(|e| e.to_string())?;
    let status = response
        .get("status")
        .and_then(|v| v.as_str())
        .unwrap_or("unknown");
    println!("Approval {approval_id} → {status}");
    Ok(())
}

pub fn run_logs(limit: usize, json: bool) -> Result<(), String> {
    let rt = build_runtime()?;
    let client = build_client();
    let limit = u32::try_from(limit).unwrap_or(u32::MAX);
    let items = rt
        .block_on(client.list_history(Some(limit)))
        .map_err(|e| e.to_string())?;

    if json {
        let body = serde_json::Value::Array(items.clone());
        println!("{}", render_json(&body));
        return Ok(());
    }

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

    Ok(())
}

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

pub fn run_policy(subcmd: &str, rest: &[String]) -> Result<(), String> {
    let mut args: Vec<&str> = vec!["policy", subcmd];
    for r in rest {
        args.push(r.as_str());
    }
    delegate_aicp(&args)
}

pub fn run_map(format: &str, file: Option<&str>) -> Result<(), String> {
    let mut args = vec!["map", format];
    if let Some(f) = file {
        args.push(f);
    }
    delegate_aicp(&args)
}

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

pub fn run_status_check() -> Result<(), String> {
    let rt = build_runtime()?;
    let client = build_client();
    let stdout = io::stdout();
    let mut lock = stdout.lock();

    match rt.block_on(client.health_check()) {
        Ok(body) => {
            writeln!(lock, "AICP runtime reachable at {}", runtime_url()).ok();
            writeln!(lock, "{}", render_json(&body)).ok();
        }
        Err(error) => {
            eprintln!("AICP runtime not reachable at {} — {error}", runtime_url());
            eprintln!("Start it with: aicp dev  OR  aicp serve");
        }
    }

    Ok(())
}
