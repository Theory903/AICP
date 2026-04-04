use runtime::{AicpConfig, ToolError, ToolExecutor};

use crate::client::AicpClient;

/// Wraps any `ToolExecutor` with AICP policy evaluation and audit recording.
///
/// This is the injection point.  It sits transparently between
/// `ConversationRuntime` and `CliToolExecutor` — neither side needs to know
/// about the other.
///
/// Lifecycle per tool call:
/// 1. **Pre-execution** — call `AicpClient::evaluate_policy`.  If denied,
///    return a `ToolError` immediately; the inner executor is never called.
/// 2. **Execution** — delegate to the wrapped `T: ToolExecutor`.
/// 3. **Post-execution** — call `AicpClient::record_audit` with the outcome.
pub struct AicpToolExecutor<T: ToolExecutor> {
    inner: T,
    client: AicpClient,
    enabled: bool,
}

impl<T: ToolExecutor> AicpToolExecutor<T> {
    /// Wrap `inner` with AICP governance.
    ///
    /// If `config.enabled` is `false` the wrapper is a transparent pass-through
    /// and no network calls are made.
    #[must_use]
    pub fn new(inner: T, config: &AicpConfig) -> Self {
        Self {
            client: AicpClient::new(config),
            enabled: config.enabled,
            inner,
        }
    }
}

impl<T: ToolExecutor> ToolExecutor for AicpToolExecutor<T> {
    fn execute(&mut self, tool_name: &str, input: &str) -> Result<String, ToolError> {
        if !self.enabled {
            // Pass-through: AICP disabled or not configured.
            return self.inner.execute(tool_name, input);
        }

        // 1. Policy gate.
        let allowed = self
            .client
            .evaluate_policy(tool_name, input)
            .unwrap_or(true); // fail-open on network error

        if !allowed {
            return Err(ToolError::new(format!(
                "AICP policy denied tool `{tool_name}`"
            )));
        }

        // 2. Execute.
        let result = self.inner.execute(tool_name, input);

        // 3. Audit.
        match &result {
            Ok(output) => {
                self.client.record_audit(tool_name, input, output, false);
            }
            Err(err) => {
                self.client
                    .record_audit(tool_name, input, &err.to_string(), true);
            }
        }

        result
    }
}
