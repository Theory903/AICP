use serde::{Deserialize, Serialize};

/// A suggested next action returned by AICP after execution.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AllowedNextAction {
    pub kind: String,
    pub name: String,
    pub reason: Option<String>,
    pub requires_approval: bool,
}

/// Policy evaluation result embedded in the envelope.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct PolicyResult {
    pub effect: String,
    pub policy_name: Option<String>,
    pub trust_tier: Option<u8>,
    pub evaluation_time_ms: Option<f64>,
}

/// The canonical execution envelope produced by the AICP runtime for every
/// capability execution.  All fields are `Option` so that a partial response
/// from the server (or a passthrough when AICP is unreachable) can still be
/// represented.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub struct ExecutionEnvelope {
    pub execution_id: Option<String>,
    pub capability_name: Option<String>,
    pub status: Option<String>,
    /// Raw tool output data.
    pub data: Option<serde_json::Value>,
    pub error: Option<String>,
    pub error_detail: Option<String>,
    pub execution_time_ms: Option<u64>,
    pub allowed_next_actions: Option<Vec<AllowedNextAction>>,
    pub rendered: Option<String>,
    pub audit_correlation_id: Option<String>,
    pub policy_result: Option<PolicyResult>,
}

impl ExecutionEnvelope {
    /// Return the best string representation of the result to show the user.
    ///
    /// Priority: `rendered` → `data` (serialised) → `error`.
    #[must_use]
    pub fn display_output(&self) -> String {
        if let Some(rendered) = &self.rendered {
            return rendered.clone();
        }
        if let Some(data) = &self.data {
            return data.to_string();
        }
        if let Some(err) = &self.error {
            return format!("AICP error: {err}");
        }
        String::new()
    }
}
