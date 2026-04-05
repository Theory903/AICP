use std::sync::Arc;

use async_trait::async_trait;
use mammoth_runtime::adapter::{ChannelAdapter, NormalizedMessage};
use mammoth_runtime::channel::{ApprovalDecision, ApprovalRequest};

pub struct BotCommand {
    pub name: &'static str,
    pub description: &'static str,
}

pub struct TelegramNormalizer;

impl TelegramNormalizer {
    pub fn normalize_command_text(&self, input: &str) -> String {
        if let Some(rest) = input.strip_prefix('/') {
            if let Some(idx) = rest.find(' ') {
                return rest[idx + 1..].to_string();
            }
        }
        input.to_string()
    }
}

pub struct TelegramAdapter {
    bot_token: String,
}

impl TelegramAdapter {
    pub fn with_token(token: &str) -> Self {
        Self {
            bot_token: token.to_string(),
        }
    }

    pub fn supported_commands() -> Vec<BotCommand> {
        vec![
            BotCommand {
                name: "ask",
                description: "Ask Mammoth a question",
            },
            BotCommand {
                name: "status",
                description: "Get Mammoth status",
            },
            BotCommand {
                name: "approve",
                description: "Approve a pending action",
            },
            BotCommand {
                name: "deny",
                description: "Deny a pending action",
            },
        ]
    }
}

#[async_trait]
impl ChannelAdapter for TelegramAdapter {
    fn platform(&self) -> &str {
        "telegram"
    }

    async fn send_message(&self, _channel_id: &str, content: &str) -> anyhow::Result<()> {
        let token_prefix = &self.bot_token[..4.min(self.bot_token.len())];
        eprintln!("telegram[{token_prefix}] send: {content}");
        Ok(())
    }

    async fn request_approval_async(
        &self,
        _channel_id: &str,
        request: &ApprovalRequest,
    ) -> anyhow::Result<ApprovalDecision> {
        Ok(ApprovalDecision {
            approval_id: request.approval_id.clone(),
            approved: false,
            comment: Some("Telegram approval not yet connected".to_string()),
            decided_by: None,
        })
    }

    async fn run(
        &self,
        on_message: Arc<dyn Fn(NormalizedMessage) -> anyhow::Result<()> + Send + Sync>,
    ) -> anyhow::Result<()> {
        eprintln!("TelegramAdapter::run called (no-op without real token)");
        let _ = on_message;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn telegram_adapter_platform_name() {
        let adapter = TelegramAdapter::with_token("test_token_123");
        assert_eq!(adapter.platform(), "telegram");
    }

    #[test]
    fn normalize_command_text_strips_slash() {
        let normalizer = TelegramNormalizer;
        let result = normalizer.normalize_command_text("/ask hello world");
        assert_eq!(result, "hello world");
    }

    #[test]
    fn approve_deny_commands_are_registered() {
        let cmds = TelegramAdapter::supported_commands();
        let names: Vec<&str> = cmds.iter().map(|c| c.name).collect();
        assert!(names.contains(&"ask"));
        assert!(names.contains(&"status"));
        assert!(names.contains(&"approve"));
        assert!(names.contains(&"deny"));
    }
}
