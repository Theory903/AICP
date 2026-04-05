use hmac::{Hmac, Mac};
use serde::{Deserialize, Serialize};
use sha2::Sha256;

type HmacSha256 = Hmac<Sha256>;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriggerRequest {
    pub session_id: String,
    pub message: String,
    pub callback_url: Option<String>,
    pub signature: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TriggerResponse {
    pub accepted: bool,
    pub execution_id: Option<String>,
}

pub struct WebhookTrigger {
    signing_secret: String,
}

impl WebhookTrigger {
    #[must_use]
    pub fn new(signing_secret: String) -> Self {
        Self { signing_secret }
    }

    #[must_use]
    pub fn compute_signature(secret: &str, body: &[u8]) -> String {
        let mut mac =
            HmacSha256::new_from_slice(secret.as_bytes()).expect("HMAC accepts any key length");
        mac.update(body);
        format!("v0={}", hex::encode(mac.finalize().into_bytes()))
    }

    #[must_use]
    pub fn verify_signature(secret: &str, provided: &str, body: &[u8]) -> bool {
        let mut mac =
            HmacSha256::new_from_slice(secret.as_bytes()).expect("HMAC accepts any key length");
        mac.update(body);
        let provided_bytes = provided
            .strip_prefix("v0=")
            .and_then(|hex_value| hex::decode(hex_value).ok());
        match provided_bytes {
            Some(bytes) => mac.verify_slice(&bytes).is_ok(),
            None => false,
        }
    }

    #[must_use]
    pub fn validate(&self, req: &TriggerRequest, raw_body: &[u8]) -> bool {
        Self::verify_signature(&self.signing_secret, &req.signature, raw_body)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn verify_hmac_accepts_correct_signature() {
        let secret = "wh_secret_123";
        let body = b"{'trigger':'deploy','env':'staging'}";
        let sig = WebhookTrigger::compute_signature(secret, body);
        assert!(WebhookTrigger::verify_signature(secret, &sig, body));
    }

    #[test]
    fn verify_hmac_rejects_wrong_secret() {
        let body = b"payload";
        let sig = WebhookTrigger::compute_signature("correct_secret", body);
        assert!(!WebhookTrigger::verify_signature(
            "wrong_secret",
            &sig,
            body
        ));
    }

    #[test]
    fn verify_hmac_rejects_tampered_body() {
        let secret = "s3cr3t";
        let sig = WebhookTrigger::compute_signature(secret, b"original");
        assert!(!WebhookTrigger::verify_signature(secret, &sig, b"tampered"));
    }

    #[test]
    fn trigger_request_deserializes() {
        let json = r#"{
            "session_id": "session-42",
            "message": "Run smoke tests",
            "callback_url": "https://ci.example.com/callback/123",
            "signature": "v0=abc123"
        }"#;
        let req: TriggerRequest = serde_json::from_str(json).expect("deserialize");
        assert_eq!(req.session_id, "session-42");
        assert_eq!(req.message, "Run smoke tests");
        assert!(req.callback_url.is_some());
    }
}
