use anyhow::{bail, Context, Result};
use url::Url;

use crate::remote::RemoteSessionContext;

#[derive(Debug, Clone)]
pub struct SshSessionConfig {
    pub host: String,
    pub port: u16,
    pub user: String,
    pub identity_file: Option<std::path::PathBuf>,
    pub host_key_verification: bool,
    pub keepalive_interval_secs: u64,
}

impl Default for SshSessionConfig {
    fn default() -> Self {
        Self {
            host: String::new(),
            port: 22,
            user: String::new(),
            identity_file: None,
            host_key_verification: true,
            keepalive_interval_secs: 30,
        }
    }
}

impl SshSessionConfig {
    pub fn from_url(url: &str) -> Result<Self> {
        let parsed = Url::parse(url).context("invalid URL")?;
        if parsed.scheme() != "ssh" {
            bail!("expected ssh:// scheme, got {}", parsed.scheme());
        }
        let host = parsed
            .host_str()
            .context("missing host in SSH URL")?
            .to_string();
        let port = parsed.port().unwrap_or(22);
        let user = if parsed.username().is_empty() {
            std::env::var("USER").unwrap_or_else(|_| "root".to_string())
        } else {
            parsed.username().to_string()
        };
        Ok(Self {
            host,
            port,
            user,
            ..Self::default()
        })
    }
}

pub struct SshSessionHandler {
    pub config: SshSessionConfig,
    pub remote_ctx: RemoteSessionContext,
}

impl SshSessionHandler {
    pub fn new(config: SshSessionConfig) -> Self {
        let base_url = format!("http://{}:{}", config.host, 3080);
        let remote_ctx = RemoteSessionContext {
            enabled: true,
            session_id: None,
            base_url,
        };
        Self { config, remote_ctx }
    }

    pub async fn connect(&mut self) -> Result<u16> {
        Ok(0)
    }

    pub async fn disconnect(&self) -> Result<()> {
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ssh_config_defaults() {
        let cfg = SshSessionConfig::default();
        assert_eq!(cfg.port, 22);
        assert!(cfg.host_key_verification);
        assert_eq!(cfg.keepalive_interval_secs, 30);
    }

    #[test]
    fn ssh_config_from_url_parses_host_and_port() {
        let cfg = SshSessionConfig::from_url("ssh://alice@remote.example.com:2222")
            .expect("parse url");
        assert_eq!(cfg.host, "remote.example.com");
        assert_eq!(cfg.user, "alice");
        assert_eq!(cfg.port, 2222);
    }

    #[test]
    fn ssh_config_from_url_uses_default_port_when_omitted() {
        let cfg = SshSessionConfig::from_url("ssh://bob@myhost.internal").expect("parse url");
        assert_eq!(cfg.host, "myhost.internal");
        assert_eq!(cfg.port, 22);
        assert_eq!(cfg.user, "bob");
    }

    #[test]
    fn ssh_config_from_url_rejects_non_ssh_scheme() {
        assert!(SshSessionConfig::from_url("https://bad.example.com").is_err());
    }
}
