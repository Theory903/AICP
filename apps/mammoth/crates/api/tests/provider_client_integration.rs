use std::ffi::OsString;
use std::sync::{Mutex, OnceLock};

use api::{ApiError, AuthSource, ProviderClient, ProviderKind};

#[test]
fn provider_client_routes_anthropic_aliases_through_anthropic() {
    let _lock = env_lock();
    let _api_key = EnvVarGuard::set("ANTHROPIC_API_KEY", Some("anthropic-test-key"));

    let client = ProviderClient::from_model("sonnet").expect("anthropic alias should resolve");

    assert_eq!(client.provider_kind(), ProviderKind::Anthropic);
}

#[test]
fn provider_client_reports_missing_anthropic_credentials_for_supported_models() {
    let _lock = env_lock();
    let _api_key = EnvVarGuard::set("ANTHROPIC_API_KEY", None);
    let _auth_token = EnvVarGuard::set("ANTHROPIC_AUTH_TOKEN", None);

    let error = ProviderClient::from_model("claude-sonnet-4-6")
        .expect_err("anthropic requests without credentials should fail fast");

    match error {
        ApiError::MissingCredentials { provider, env_vars } => {
            assert_eq!(provider, "Mammoth");
            assert_eq!(env_vars, &["ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_API_KEY"]);
        }
        other => panic!("expected missing Anthropic credentials, got {other:?}"),
    }
}

#[test]
fn provider_client_uses_explicit_auth_without_env_lookup() {
    let _lock = env_lock();
    let _api_key = EnvVarGuard::set("ANTHROPIC_API_KEY", None);
    let _auth_token = EnvVarGuard::set("ANTHROPIC_AUTH_TOKEN", None);

    let client = ProviderClient::from_model_with_default_auth(
        "claude-sonnet-4-6",
        Some(AuthSource::ApiKey("mammoth-test-key".to_string())),
    )
    .expect("explicit auth should avoid env lookup");

    assert_eq!(client.provider_kind(), ProviderKind::Anthropic);
}

fn env_lock() -> std::sync::MutexGuard<'static, ()> {
    static LOCK: OnceLock<Mutex<()>> = OnceLock::new();
    LOCK.get_or_init(|| Mutex::new(()))
        .lock()
        .unwrap_or_else(|poisoned| poisoned.into_inner())
}

struct EnvVarGuard {
    key: &'static str,
    original: Option<OsString>,
}

impl EnvVarGuard {
    fn set(key: &'static str, value: Option<&str>) -> Self {
        let original = std::env::var_os(key);
        match value {
            Some(value) => unsafe { std::env::set_var(key, value) },
            None => unsafe { std::env::remove_var(key) },
        }
        Self { key, original }
    }
}

impl Drop for EnvVarGuard {
    fn drop(&mut self) {
        match &self.original {
            Some(value) => unsafe { std::env::set_var(self.key, value) },
            None => unsafe { std::env::remove_var(self.key) },
        }
    }
}
