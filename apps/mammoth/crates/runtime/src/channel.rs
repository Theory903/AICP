//! Channel abstraction for the Mammoth Interaction OS.
//!
//! Every way a human or agent touches Mammoth goes through a Channel.
//! Channels are the four surfaces of the Mammoth Interaction OS:
//!
//! - `Terminal`  — conversational REPL (`mammoth-cli`)
//! - `Web`       — Studio supervision console + chat UI (`server` crate / axum)
//! - `Cli`       — multi-channel command dispatcher (`mammoth serve`, `mammoth ext`, …)
//! - `Extension` — Chrome MV3 extension bridged via SSE
//!
//! All channels funnel intent into the AICP execution layer (policy eval, audit,
//! approval gating, `allowed_next_actions`) and receive back an `ExecutionEnvelope`.

use serde::{Deserialize, Serialize};

// ---------------------------------------------------------------------------
// ChannelKind
// ---------------------------------------------------------------------------

/// Identifies which Mammoth channel is originating a request.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ChannelKind {
    /// Terminal REPL (`mammoth` binary, interactive or non-interactive).
    Terminal,
    /// Web channel — Studio UI served by the `server` crate.
    Web,
    /// CLI sub-commands (`mammoth serve`, `mammoth ext`, etc.).
    Cli,
    /// Chrome MV3 extension, bridged via the extension bridge SSE endpoint.
    Extension,
}

impl std::fmt::Display for ChannelKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Terminal => write!(f, "terminal"),
            Self::Web => write!(f, "web"),
            Self::Cli => write!(f, "cli"),
            Self::Extension => write!(f, "extension"),
        }
    }
}

// ---------------------------------------------------------------------------
// ApprovalRequest / ApprovalDecision
// ---------------------------------------------------------------------------

/// An approval request surfaced from the AICP execution layer to the channel.
///
/// When the policy engine sets `effect = "require_approval"`, the runtime
/// emits an `ApprovalRequest` and pauses execution until the channel delivers
/// an `ApprovalDecision`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApprovalRequest {
    /// Unique identifier for this approval checkpoint.
    pub approval_id: String,
    /// The capability name that requires human sign-off.
    pub capability_name: String,
    /// Human-readable description of the action to be taken.
    pub description: String,
    /// Risk metadata from the AICP policy engine.
    pub risk_summary: Option<String>,
    /// Channel that should present this request to the human.
    pub channel: ChannelKind,
}

/// The human's response to an `ApprovalRequest`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApprovalDecision {
    /// Must match the originating `ApprovalRequest::approval_id`.
    pub approval_id: String,
    /// `true` = approved, `false` = denied.
    pub approved: bool,
    /// Optional free-text comment from the human (shown in audit trail).
    pub comment: Option<String>,
    /// Who made the decision (user id, extension context, etc.).
    pub decided_by: Option<String>,
}

// ---------------------------------------------------------------------------
// Channel trait
// ---------------------------------------------------------------------------

/// The core abstraction every Mammoth channel must implement.
///
/// Channels are responsible for:
/// 1. Receiving user intent (text, tool calls, events).
/// 2. Handing intent to the AICP execution layer.
/// 3. Rendering the resulting `ExecutionEnvelope` back to the user.
/// 4. Presenting `ApprovalRequest`s and collecting `ApprovalDecision`s.
///
/// Channels MUST NOT contain orchestration logic. They translate only.
pub trait Channel: Send + Sync {
    /// Human-readable name of this channel instance (e.g. `"terminal"`, `"web"`).
    fn name(&self) -> &str;

    /// Which kind of surface this channel represents.
    fn kind(&self) -> ChannelKind;

    /// Render a plain text or markdown message to the channel's output surface.
    fn render_message(&self, content: &str);

    /// Present an approval request to the human and return their decision.
    ///
    /// Implementations MUST block (or `.await`) until the user responds.
    /// The returned `ApprovalDecision::approval_id` MUST match `request.approval_id`.
    fn request_approval(&self, request: &ApprovalRequest) -> ApprovalDecision;

    /// Called by the runtime after every tool execution to surface progress.
    ///
    /// Default implementation is a no-op; override to show spinners, progress
    /// bars, or structured JSON events depending on the channel surface.
    fn on_tool_progress(&self, _tool_name: &str, _message: &str) {}

    /// Called when the channel is shutting down. Release any resources here.
    fn shutdown(&self) {}
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    struct NoOpChannel;

    impl Channel for NoOpChannel {
        fn name(&self) -> &str {
            "noop"
        }
        fn kind(&self) -> ChannelKind {
            ChannelKind::Terminal
        }
        fn render_message(&self, _content: &str) {}
        fn request_approval(&self, request: &ApprovalRequest) -> ApprovalDecision {
            ApprovalDecision {
                approval_id: request.approval_id.clone(),
                approved: true,
                comment: None,
                decided_by: None,
            }
        }
    }

    #[test]
    fn channel_kind_display() {
        assert_eq!(ChannelKind::Terminal.to_string(), "terminal");
        assert_eq!(ChannelKind::Web.to_string(), "web");
        assert_eq!(ChannelKind::Cli.to_string(), "cli");
        assert_eq!(ChannelKind::Extension.to_string(), "extension");
    }

    #[test]
    fn channel_kind_serde_roundtrip() {
        let kind = ChannelKind::Extension;
        let json = serde_json::to_string(&kind).expect("serialize");
        assert_eq!(json, "\"extension\"");
        let back: ChannelKind = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(back, kind);
    }

    #[test]
    fn approval_roundtrip() {
        let req = ApprovalRequest {
            approval_id: "appr_001".to_string(),
            capability_name: "orders.place".to_string(),
            description: "Place order for $49.99".to_string(),
            risk_summary: Some("financial: 0.7, irreversibility: 0.9".to_string()),
            channel: ChannelKind::Web,
        };
        let json = serde_json::to_string(&req).expect("serialize");
        let back: ApprovalRequest = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(back, req);
    }

    #[test]
    fn noop_channel_auto_approves() {
        let ch = NoOpChannel;
        let req = ApprovalRequest {
            approval_id: "appr_test".to_string(),
            capability_name: "files.delete".to_string(),
            description: "Delete /tmp/foo".to_string(),
            risk_summary: None,
            channel: ChannelKind::Terminal,
        };
        let decision = ch.request_approval(&req);
        assert_eq!(decision.approval_id, req.approval_id);
        assert!(decision.approved);
    }
}
