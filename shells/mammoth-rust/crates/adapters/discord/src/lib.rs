use std::sync::Arc;

use async_trait::async_trait;
use mammoth_runtime::adapter::{ChannelAdapter, NormalizedMessage};
use mammoth_runtime::channel::{ApprovalDecision, ApprovalRequest};

#[derive(Debug, Clone)]
pub struct SlashCommandDef {
    pub name: String,
    pub description: String,
}

pub fn extract_string_option(opts: &[(&str, &str)], name: &str) -> Option<String> {
    opts.iter()
        .find(|(k, _)| *k == name)
        .map(|(_, v)| v.to_string())
}

pub struct DiscordAdapter {
    bot_token: String,
    application_id: u64,
}

impl DiscordAdapter {
    pub fn with_token(token: &str, app_id: u64) -> Self {
        Self {
            bot_token: token.to_string(),
            application_id: app_id,
        }
    }

    pub fn supported_slash_commands() -> Vec<SlashCommandDef> {
        vec![
            SlashCommandDef {
                name: "ask".to_string(),
                description: "Ask Mammoth a question".to_string(),
            },
            SlashCommandDef {
                name: "status".to_string(),
                description: "Get Mammoth status".to_string(),
            },
            SlashCommandDef {
                name: "approve".to_string(),
                description: "Approve a pending action".to_string(),
            },
            SlashCommandDef {
                name: "deny".to_string(),
                description: "Deny a pending action".to_string(),
            },
        ]
    }
}

#[async_trait]
impl ChannelAdapter for DiscordAdapter {
    fn platform(&self) -> &str {
        let _ = (&self.bot_token, self.application_id);
        "discord"
    }

    async fn send_message(&self, _channel_id: &str, content: &str) -> anyhow::Result<()> {
        eprintln!("[discord] send: {content}");
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
            comment: Some("Discord approval not yet connected".to_string()),
            decided_by: None,
        })
    }

    async fn run(
        &self,
        on_message: Arc<dyn Fn(NormalizedMessage) -> anyhow::Result<()> + Send + Sync>,
    ) -> anyhow::Result<()> {
        let _ = on_message;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn discord_adapter_platform_name() {
        let adapter = DiscordAdapter::with_token("test_tok", 123456789u64);
        assert_eq!(adapter.platform(), "discord");
    }

    #[test]
    fn discord_supported_slash_commands() {
        let cmds = DiscordAdapter::supported_slash_commands();
        let names: Vec<&str> = cmds.iter().map(|c| c.name.as_str()).collect();
        assert!(names.contains(&"ask"));
        assert!(names.contains(&"status"));
        assert!(names.contains(&"approve"));
        assert!(names.contains(&"deny"));
    }

    #[test]
    fn interaction_option_extraction() {
        let extracted = extract_string_option(&[("text", "deploy to prod")], "text");
        assert_eq!(extracted, Some("deploy to prod".to_string()));
        assert_eq!(extract_string_option(&[], "text"), None);
    }
}
