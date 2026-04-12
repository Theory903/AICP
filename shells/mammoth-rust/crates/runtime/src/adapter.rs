use std::collections::HashMap;
use std::sync::Arc;

use async_trait::async_trait;
use serde::{Deserialize, Serialize};

use crate::channel::{ApprovalDecision, ApprovalRequest};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct NormalizedMessage {
    pub platform: String,
    pub channel_id: String,
    pub sender_id: String,
    pub text: String,
    #[serde(default)]
    pub metadata: HashMap<String, String>,
}

pub trait MessageNormalizer: Send + Sync {
    type PlatformMessage;

    fn normalize(&self, msg: &Self::PlatformMessage) -> NormalizedMessage;
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "platform", rename_all = "snake_case")]
pub enum AdapterConfig {
    Telegram { bot_token: String },
    Discord { bot_token: String, application_id: u64 },
    Slack {
        bot_token: String,
        signing_secret: String,
        app_token: Option<String>,
    },
}

#[async_trait]
pub trait ChannelAdapter: Send + Sync {
    fn platform(&self) -> &str;
    async fn send_message(&self, channel_id: &str, content: &str) -> anyhow::Result<()>;
    async fn request_approval_async(
        &self,
        channel_id: &str,
        request: &ApprovalRequest,
    ) -> anyhow::Result<ApprovalDecision>;
    async fn register_commands(&self) -> anyhow::Result<()> {
        Ok(())
    }
    async fn run(
        &self,
        on_message: Arc<dyn Fn(NormalizedMessage) -> anyhow::Result<()> + Send + Sync>,
    ) -> anyhow::Result<()>;
    async fn shutdown(&self) -> anyhow::Result<()> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn normalized_message_roundtrip() {
        let msg = NormalizedMessage {
            platform: "telegram".to_string(),
            channel_id: "chat_123".to_string(),
            sender_id: "user_456".to_string(),
            text: "Hello Mammoth".to_string(),
            metadata: Default::default(),
        };
        let json = serde_json::to_string(&msg).expect("serialize");
        let back: NormalizedMessage = serde_json::from_str(&json).expect("deserialize");
        assert_eq!(back.text, "Hello Mammoth");
        assert_eq!(back.platform, "telegram");
    }

    #[test]
    fn adapter_config_telegram_variant() {
        let cfg = AdapterConfig::Telegram {
            bot_token: "tok_abc".to_string(),
        };
        let json = serde_json::to_string(&cfg).expect("serialize");
        assert!(json.contains("telegram"));
        assert!(json.contains("tok_abc"));
    }
}
