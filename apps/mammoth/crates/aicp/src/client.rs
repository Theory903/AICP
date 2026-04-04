use reqwest::blocking::Client;
use runtime::AicpConfig;
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

/// Blocking HTTP client for the AICP runtime.
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
    ///
    /// Returns `Ok(true)` if AICP allows the action, `Ok(false)` if denied.
    /// On network error the call is **fail-open** (returns `Ok(true)`) so that
    /// Mammoth keeps working when AICP is not running.
    pub fn evaluate_policy(&self, tool_name: &str, input: &str) -> Result<bool, AicpError> {
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
            .map_err(|e| AicpError::Unreachable(e.to_string()))?;

        let status = response.status();
        let text = response
            .text()
            .map_err(|e| AicpError::BadResponse(e.to_string()))?;

        if !status.is_success() {
            // Fail-open: allow if the policy endpoint is unavailable.
            return Ok(true);
        }

        let parsed: Value =
            serde_json::from_str(&text).map_err(|e| AicpError::Json(e.to_string()))?;

        let effect = parsed
            .get("effect")
            .and_then(|v| v.as_str())
            .unwrap_or("allow");

        Ok(effect == "allow")
    }

    /// Record a completed tool execution in the AICP audit trail.
    ///
    /// Errors are silently swallowed — audit failures must never block execution.
    pub fn record_audit(&self, tool_name: &str, input: &str, output: &str, is_error: bool) {
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

        // Best-effort — ignore any error.
        let _ = self.http.post(&url).json(&body).send();
    }

    /// Execute a capability through AICP's full governed execution path.
    ///
    /// Returns the `ExecutionEnvelope` on success.
    pub fn execute(
        &self,
        capability_name: &str,
        input: &str,
    ) -> Result<ExecutionEnvelope, AicpError> {
        let url = format!("{}/v1/execute", self.base_url);

        let input_value: Value =
            serde_json::from_str(input).unwrap_or_else(|_| json!({ "raw": input }));

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
            .map_err(|e| AicpError::Unreachable(e.to_string()))?;

        let text = response
            .text()
            .map_err(|e| AicpError::BadResponse(e.to_string()))?;

        serde_json::from_str(&text).map_err(|e| AicpError::Json(e.to_string()))
    }
}
