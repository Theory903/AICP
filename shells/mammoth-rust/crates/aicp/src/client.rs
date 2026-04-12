use reqwest::Client;
use mammoth_runtime::AicpConfig;
use serde_json::{json, Value};

use crate::envelope::ExecutionEnvelope;

/// Error returned by `AicpClient` operations.
#[derive(Debug)]
pub enum AicpError {
    /// The AICP runtime could not be reached (network error, not running, etc).
    Unreachable(String),
    /// The server returned an unexpected response.
    BadResponse(String),
    /// JSON serialisation / deserialisation failed.
    Json(String),
}

impl std::fmt::Display for AicpError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Unreachable(msg) => write!(f, "AICP unreachable: {msg}"),
            Self::BadResponse(msg) => write!(f, "AICP bad response: {msg}"),
            Self::Json(msg) => write!(f, "AICP JSON error: {msg}"),
        }
    }
}

impl std::error::Error for AicpError {}

/// Async HTTP client for the AICP runtime.
#[derive(Clone)]
pub struct AicpClient {
    base_url: String,
    trust_tier: String,
    session_id: Option<String>,
    http: Client,
}

impl AicpClient {
    /// Construct a client from an `AicpConfig`.
    #[must_use]
    pub fn new(config: &AicpConfig) -> Self {
        Self {
            base_url: config.resolve_url(),
            trust_tier: config.trust_tier.clone(),
            session_id: config.session_id.clone(),
            http: Client::new(),
        }
    }

    /// Fire a pre-execution policy evaluation for a tool call.
    pub async fn evaluate_policy(&self, tool_name: &str, input: &str) -> Result<bool, AicpError> {
        let url = format!("{}/v1/policy/evaluate", self.base_url);
        let body = json!({
            "capability_name": tool_name,
            "input": input,
            "trust_tier": self.trust_tier,
            "session_id": self.session_id,
        });

        let response = self
            .http
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| AicpError::Unreachable(e.to_string()))?;

        if !response.status().is_success() {
            return Ok(true);
        }

        let parsed: Value = response
            .json()
            .await
            .map_err(|e| AicpError::Json(e.to_string()))?;

        let effect = parsed
            .get("effect")
            .and_then(|v| v.as_str())
            .unwrap_or("allow");

        Ok(effect == "allow")
    }

    /// Record a completed tool execution in the AICP audit trail.
    pub async fn record_audit(&self, tool_name: &str, input: &str, output: &str, is_error: bool) {
        let url = format!("{}/v1/audit", self.base_url);
        let body = json!({
            "capability_name": tool_name,
            "input": input,
            "output": output,
            "is_error": is_error,
            "trust_tier": self.trust_tier,
            "session_id": self.session_id,
            "actor": { "type": "agent" },
        });

        let _ = self.http.post(&url).json(&body).send().await;
    }

    /// Execute a capability through AICP's full governed execution path.
    pub async fn execute(
        &self,
        capability_name: &str,
        input: &str,
    ) -> Result<ExecutionEnvelope, AicpError> {
        let url = format!("{}/v1/execute", self.base_url);
        let input_value: Value = serde_json::from_str(input).unwrap_or_else(|_| json!({ "raw": input }));

        let body = json!({
            "capability_name": capability_name,
            "input": input_value,
            "trust_tier": self.trust_tier,
            "session_id": self.session_id,
        });

        let response = self
            .http
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| AicpError::Unreachable(e.to_string()))?;

        response.json().await.map_err(|e| AicpError::Json(e.to_string()))
    }

    /// List registered capabilities.
    pub async fn list_capabilities(&self) -> Result<Vec<Value>, AicpError> {
        let url = format!("{}/discover", self.base_url);
        let response = self
            .http
            .get(&url)
            .send()
            .await
            .map_err(|e| AicpError::Unreachable(e.to_string()))?;

        let val: Value = response.json().await.map_err(|e| AicpError::Json(e.to_string()))?;
        let caps = val.get("capabilities")
            .or_else(|| val.as_array().map(|_| &val))
            .and_then(|v| v.as_array())
            .cloned()
            .unwrap_or_default();
        Ok(caps)
    }

    /// List pending approvals.
    pub async fn list_approvals(&self) -> Result<Vec<Value>, AicpError> {
        let url = format!("{}/approvals", self.base_url);
        let response = self
            .http
            .get(&url)
            .send()
            .await
            .map_err(|e| AicpError::Unreachable(e.to_string()))?;

        response.json().await.map_err(|e| AicpError::Json(e.to_string()))
    }

    /// Decide on a pending approval.
    pub async fn decide_approval(&self, id: &str, decision: &str, reason: &str) -> Result<Value, AicpError> {
        let url = format!("{}/approvals/{}/decide", self.base_url, id);
        let body = json!({
            "decision": decision,
            "reason": reason
        });

        let response = self
            .http
            .post(&url)
            .json(&body)
            .send()
            .await
            .map_err(|e| AicpError::Unreachable(e.to_string()))?;

        response.json().await.map_err(|e| AicpError::Json(e.to_string()))
    }

    pub async fn list_history(&self, limit: Option<u32>) -> Result<Vec<serde_json::Value>, AicpError> {
        let url = match limit {
            Some(n) => format!("{}/history?limit={}", self.base_url, n),
            None => format!("{}/history", self.base_url),
        };
        let response = self
            .http
            .get(&url)
            .send()
            .await
            .map_err(|e| AicpError::Unreachable(e.to_string()))?;
        response.json().await.map_err(|e| AicpError::Json(e.to_string()))
    }

    pub async fn health_check(&self) -> Result<serde_json::Value, AicpError> {
        let url = format!("{}/providers/health", self.base_url);
        let response = self
            .http
            .get(&url)
            .send()
            .await
            .map_err(|e| AicpError::Unreachable(e.to_string()))?;
        response.json().await.map_err(|e| AicpError::Json(e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::AicpClient;
    use mammoth_runtime::AicpConfig;
    use std::io::{Read, Write};
    use std::net::TcpListener;

    fn serve_once(status_line: &str, body: &str) -> String {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind test listener");
        let address = format!("http://{}", listener.local_addr().expect("read listener addr"));
        let response_body = body.to_string();
        let status = status_line.to_string();

        std::thread::spawn(move || {
            let (mut stream, _) = listener.accept().expect("accept request");
            let mut buffer = [0_u8; 4096];
            let _ = stream.read(&mut buffer).expect("read request");
            let response = format!(
                "HTTP/1.1 {status}\r\ncontent-type: application/json\r\ncontent-length: {}\r\nconnection: close\r\n\r\n{}",
                response_body.len(),
                response_body
            );
            stream
                .write_all(response.as_bytes())
                .expect("write response");
        });

        address
    }

    #[test]
    fn list_history_requests_history_endpoint() {
        let base_url = serve_once(
            "200 OK",
            r#"[{"execution_id":"exec_123","status":"success"}]"#,
        );
        let client = AicpClient::new(&AicpConfig {
            url: base_url,
            ..AicpConfig::default()
        });
        let runtime = tokio::runtime::Runtime::new().expect("create tokio runtime");

        let history = runtime
            .block_on(client.list_history(Some(5)))
            .expect("history should parse");

        assert_eq!(history.len(), 1);
        assert_eq!(history[0]["execution_id"], "exec_123");
    }

    #[test]
    fn health_check_requests_provider_health_endpoint() {
        let base_url = serve_once("200 OK", r#"{"provider":"ok"}"#);
        let client = AicpClient::new(&AicpConfig {
            url: base_url,
            ..AicpConfig::default()
        });
        let runtime = tokio::runtime::Runtime::new().expect("create tokio runtime");

        let health = runtime
            .block_on(client.health_check())
            .expect("health should parse");

        assert_eq!(health["provider"], "ok");
    }
}
