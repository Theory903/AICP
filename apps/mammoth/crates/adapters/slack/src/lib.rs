use std::sync::Arc;

use serde_json::json;

use mammoth_runtime::adapter::NormalizedMessage;

pub struct SlackAdapter {
    bot_token: String,
    signing_secret: String,
    app_token: Option<String>,
}

impl SlackAdapter {
    pub fn with_credentials(bot_token: &str, signing_secret: &str, app_token: Option<&str>) -> Self {
        Self {
            bot_token: bot_token.to_string(),
            signing_secret: signing_secret.to_string(),
            app_token: app_token.map(str::to_string),
        }
    }

    pub fn build_approval_blocks(
        approval_id: &str,
        capability_name: &str,
        description: &str,
    ) -> serde_json::Value {
        json!({
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": format!("*Approval Required*: `{capability_name}`\n{description}")
                    }
                },
                {
                    "type": "actions",
                    "elements": [
                        {
                            "type": "button",
                            "text": { "type": "plain_text", "text": "✅ Approve" },
                            "style": "primary",
                            "action_id": format!("approve_{approval_id}"),
                            "value": approval_id
                        },
                        {
                            "type": "button",
                            "text": { "type": "plain_text", "text": "❌ Deny" },
                            "style": "danger",
                            "action_id": format!("deny_{approval_id}"),
                            "value": approval_id
                        }
                    ]
                }
            ]
        })
    }

    pub fn verify_signature(secret: &str, sig_header: &str, timestamp: &str, body: &[u8]) -> bool {
        use hmac::{Hmac, Mac};
        use sha2::Sha256;

        let base_string = format!("v0:{timestamp}:{}", std::str::from_utf8(body).unwrap_or(""));
        let Ok(mut mac) = Hmac::<Sha256>::new_from_slice(secret.as_bytes()) else {
            return false;
        };
        mac.update(base_string.as_bytes());
        let computed = format!("v0={}", hex::encode(mac.finalize().into_bytes()));
        computed == sig_header
    }
}

#[async_trait::async_trait]
impl mammoth_runtime::adapter::ChannelAdapter for SlackAdapter {
    fn platform(&self) -> &str {
        let _ = (&self.bot_token, &self.signing_secret, &self.app_token);
        "slack"
    }

    async fn send_message(&self, _channel_id: &str, content: &str) -> anyhow::Result<()> {
        let _ = (&self.bot_token, &self.signing_secret, &self.app_token);
        eprintln!("[slack] send: {content}");
        Ok(())
    }

    async fn request_approval_async(
        &self,
        _channel_id: &str,
        request: &mammoth_runtime::channel::ApprovalRequest,
    ) -> anyhow::Result<mammoth_runtime::channel::ApprovalDecision> {
        Ok(mammoth_runtime::channel::ApprovalDecision {
            approval_id: request.approval_id.clone(),
            approved: false,
            comment: Some("Slack approval not yet connected".to_string()),
            decided_by: None,
        })
    }

    async fn run(
        &self,
        on_message: Arc<dyn Fn(NormalizedMessage) -> anyhow::Result<()> + Send + Sync>,
    ) -> anyhow::Result<()> {
        let _ = (&self.bot_token, &self.signing_secret, &self.app_token);
        let _ = on_message;
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use mammoth_runtime::adapter::ChannelAdapter;

    #[test]
    fn slack_adapter_platform_name() {
        let adapter = SlackAdapter::with_credentials(
            "xoxb-test-token",
            "signing_secret_abc",
            None,
        );
        assert_eq!(adapter.platform(), "slack");
    }

    #[test]
    fn block_kit_approval_blocks_contain_action_ids() {
        let blocks = SlackAdapter::build_approval_blocks("appr_001", "files.delete", "Delete /tmp/x");
        let json = serde_json::to_string(&blocks).expect("serialize");
        assert!(json.contains("approve_appr_001"));
        assert!(json.contains("deny_appr_001"));
    }

    #[test]
    fn verify_signature_rejects_bad_secret() {
        let result = SlackAdapter::verify_signature(
            "wrong_secret",
            "v0=bad_sig",
            "1234567890",
            b"payload",
        );
        assert!(!result);
    }

    #[test]
    fn verify_signature_accepts_correct_hmac() {
        use hmac::{Hmac, Mac};
        use sha2::Sha256;
        let secret = "test_secret";
        let ts = "1609459200";
        let body = b"payload=test";
        let base = format!("v0:{ts}:{}", std::str::from_utf8(body).unwrap());
        let mut mac = Hmac::<Sha256>::new_from_slice(secret.as_bytes()).unwrap();
        mac.update(base.as_bytes());
        let expected = format!("v0={}", hex::encode(mac.finalize().into_bytes()));
        assert!(SlackAdapter::verify_signature(secret, &expected, ts, body));
    }
}
