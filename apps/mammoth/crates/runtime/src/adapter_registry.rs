use std::fs;
use std::path::Path;
use std::sync::Arc;

use anyhow::Context;
use serde::{Deserialize, Serialize};

#[allow(unused_imports)]
use crate::adapter::{AdapterConfig, ChannelAdapter, NormalizedMessage};
use crate::channel::{ApprovalDecision, ApprovalRequest};

#[derive(Debug, Clone, Default, Serialize, Deserialize, PartialEq, Eq)]
pub struct ChannelsConfig {
    #[serde(default)]
    pub channels: Vec<AdapterConfig>,
}

pub fn parse_optional_channels_config(cwd: impl AsRef<Path>) -> anyhow::Result<Option<ChannelsConfig>> {
    let path = cwd.as_ref().join("mammoth.toml");
    let contents = match fs::read_to_string(&path) {
        Ok(contents) => contents,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(error) => return Err(error.into()),
    };

    if contents.trim().is_empty() {
        return Ok(Some(ChannelsConfig::default()));
    }

    toml::from_str(&contents)
        .map(Some)
        .with_context(|| format!("failed to parse {}", path.display()))
}

pub struct ChannelAdapterRegistry {
    adapters: Vec<Arc<dyn ChannelAdapter>>,
}

impl ChannelAdapterRegistry {
    #[must_use]
    pub fn new() -> Self {
        Self { adapters: vec![] }
    }

    pub fn register(&mut self, adapter: Arc<dyn ChannelAdapter>) {
        self.adapters.push(adapter);
    }

    pub async fn broadcast(&self, channel_id: &str, content: &str) {
        for adapter in &self.adapters {
            if let Err(err) = adapter.send_message(channel_id, content).await {
                tracing::warn!(
                    platform = adapter.platform(),
                    channel_id,
                    error = %err,
                    "adapter send_message failed during broadcast"
                );
            }
        }
    }

    #[must_use]
    pub fn platform_names(&self) -> Vec<&str> {
        self.adapters.iter().map(|adapter| adapter.platform()).collect()
    }

    pub async fn request_approval_fanout(
        &self,
        channel_id: &str,
        request: &ApprovalRequest,
    ) -> Option<ApprovalDecision> {
        for adapter in &self.adapters {
            match adapter.request_approval_async(channel_id, request).await {
                Ok(decision) => return Some(decision),
                Err(err) => {
                    tracing::warn!(
                        platform = adapter.platform(),
                        error = %err,
                        "adapter request_approval_async failed"
                    );
                }
            }
        }

        None
    }

    pub async fn shutdown_all(&self) {
        for adapter in &self.adapters {
            if let Err(err) = adapter.shutdown().await {
                tracing::warn!(
                    platform = adapter.platform(),
                    error = %err,
                    "adapter shutdown failed"
                );
            }
        }
    }
}

impl Default for ChannelAdapterRegistry {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use std::sync::{Arc, Mutex};

    use super::*;

    struct RecordingAdapter {
        name: String,
        sent: Arc<Mutex<Vec<String>>>,
    }

    #[async_trait::async_trait]
    impl ChannelAdapter for RecordingAdapter {
        fn platform(&self) -> &str {
            &self.name
        }

        async fn send_message(&self, _channel_id: &str, content: &str) -> anyhow::Result<()> {
            self.sent.lock().unwrap().push(content.to_string());
            Ok(())
        }

        async fn request_approval_async(
            &self,
            _channel_id: &str,
            req: &ApprovalRequest,
        ) -> anyhow::Result<ApprovalDecision> {
            Ok(ApprovalDecision {
                approval_id: req.approval_id.clone(),
                approved: true,
                comment: None,
                decided_by: Some("test".to_string()),
            })
        }

        async fn run(
            &self,
            _on_message: Arc<dyn Fn(NormalizedMessage) -> anyhow::Result<()> + Send + Sync>,
        ) -> anyhow::Result<()> {
            Ok(())
        }
    }

    #[tokio::test]
    async fn fanout_broadcasts_to_all_adapters() {
        let sent_a = Arc::new(Mutex::new(vec![]));
        let sent_b = Arc::new(Mutex::new(vec![]));
        let mut registry = ChannelAdapterRegistry::new();
        registry.register(Arc::new(RecordingAdapter {
            name: "a".to_string(),
            sent: sent_a.clone(),
        }));
        registry.register(Arc::new(RecordingAdapter {
            name: "b".to_string(),
            sent: sent_b.clone(),
        }));

        registry.broadcast("ch_1", "hello from mammoth").await;

        assert_eq!(*sent_a.lock().unwrap(), vec!["hello from mammoth"]);
        assert_eq!(*sent_b.lock().unwrap(), vec!["hello from mammoth"]);
    }

    #[tokio::test]
    async fn registry_lists_registered_platform_names() {
        let mut registry = ChannelAdapterRegistry::new();
        registry.register(Arc::new(RecordingAdapter {
            name: "telegram".to_string(),
            sent: Default::default(),
        }));
        registry.register(Arc::new(RecordingAdapter {
            name: "discord".to_string(),
            sent: Default::default(),
        }));

        let names = registry.platform_names();

        assert!(names.contains(&"telegram"));
        assert!(names.contains(&"discord"));
        assert_eq!(names.len(), 2);
    }

    #[test]
    fn parse_channels_config_from_toml() {
        let toml_str = r#"
[[channels]]
platform = "telegram"
bot_token = "tg_tok_abc"

[[channels]]
platform = "discord"
bot_token = "dc_tok_xyz"
application_id = 123456789
"#;

        let configs: ChannelsConfig = toml::from_str(toml_str).expect("parse");

        assert_eq!(configs.channels.len(), 2);
        match &configs.channels[0] {
            AdapterConfig::Telegram { bot_token } => assert_eq!(bot_token, "tg_tok_abc"),
            _ => panic!("expected Telegram"),
        }
    }
}
