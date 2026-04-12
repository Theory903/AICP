use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PluginListing {
    pub id: String,
    pub name: String,
    pub description: String,
    pub latest_version: String,
    pub download_url: String,
    pub signature_url: String,
    pub publisher_key_url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VersionEntry {
    pub version: String,
    pub download_url: String,
    pub signature_url: String,
    pub released_at: String,
}

#[derive(Debug)]
pub enum RegistryError {
    Ssrf(String),
    Http(String),
    Parse(String),
}

impl std::fmt::Display for RegistryError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::Ssrf(s) | Self::Http(s) | Self::Parse(s) => write!(f, "{s}"),
        }
    }
}

pub struct RegistryClient {
    base_url: String,
    client: reqwest::blocking::Client,
}

impl RegistryClient {
    pub fn new(base_url: impl Into<String>) -> Self {
        Self {
            base_url: base_url.into(),
            client: reqwest::blocking::Client::new(),
        }
    }

    fn check_ssrf(&self, url: &str) -> Result<(), RegistryError> {
        use mammoth_runtime::security::{SsrfCheckResult, SsrfGuard};
        match SsrfGuard::default().check_url(url) {
            SsrfCheckResult::Allowed => Ok(()),
            SsrfCheckResult::Blocked { reason } => Err(RegistryError::Ssrf(reason)),
        }
    }

    pub fn search(&self, query: &str) -> Result<Vec<PluginListing>, RegistryError> {
        let url = format!("{}/v1/plugins?q={}", self.base_url, query);
        self.check_ssrf(&url)?;
        let resp: serde_json::Value = self
            .client
            .get(&url)
            .send()
            .map_err(|e| RegistryError::Http(e.to_string()))?
            .json()
            .map_err(|e| RegistryError::Parse(e.to_string()))?;
        serde_json::from_value(resp["plugins"].clone())
            .map_err(|e| RegistryError::Parse(e.to_string()))
    }

    pub fn get_plugin(&self, id: &str) -> Result<Option<PluginListing>, RegistryError> {
        let url = format!("{}/v1/plugins/{}", self.base_url, id);
        self.check_ssrf(&url)?;
        let resp = self
            .client
            .get(&url)
            .send()
            .map_err(|e| RegistryError::Http(e.to_string()))?;
        if resp.status() == reqwest::StatusCode::NOT_FOUND {
            return Ok(None);
        }
        resp.json::<PluginListing>()
            .map(Some)
            .map_err(|e| RegistryError::Parse(e.to_string()))
    }

    pub fn get_versions(&self, id: &str) -> Result<Vec<VersionEntry>, RegistryError> {
        let url = format!("{}/v1/plugins/{}/versions", self.base_url, id);
        self.check_ssrf(&url)?;
        let resp: serde_json::Value = self
            .client
            .get(&url)
            .send()
            .map_err(|e| RegistryError::Http(e.to_string()))?
            .json()
            .map_err(|e| RegistryError::Parse(e.to_string()))?;
        serde_json::from_value(resp["versions"].clone())
            .map_err(|e| RegistryError::Parse(e.to_string()))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn search_deserializes_plugin_listing() {
        let mut server = mockito::Server::new();
        let _mock = server
            .mock("GET", "/v1/plugins?q=git")
            .with_body(
                r#"{"plugins":[{"id":"git-helper","name":"Git Helper","description":"Git tools","latest_version":"1.0.0","download_url":"https://example.com/git-helper.tar.gz","signature_url":"https://example.com/git-helper.sig","publisher_key_url":"https://example.com/key.pub"}]}"#,
            )
            .create();
        let client = RegistryClient::new(server.url());
        let results = client.search("git").unwrap();
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].id, "git-helper");
    }

    #[test]
    fn get_plugin_returns_none_on_404() {
        let mut server = mockito::Server::new();
        let _mock = server
            .mock("GET", "/v1/plugins/nonexistent")
            .with_status(404)
            .create();
        let client = RegistryClient::new(server.url());
        let result = client.get_plugin("nonexistent").unwrap();
        assert!(result.is_none());
    }

    #[test]
    fn get_versions_deserializes_entries() {
        let mut server = mockito::Server::new();
        let _mock = server
            .mock("GET", "/v1/plugins/git-helper/versions")
            .with_body(
                r#"{"versions":[{"version":"1.0.0","download_url":"https://example.com/v1.tar.gz","signature_url":"https://example.com/v1.sig","released_at":"2026-01-01T00:00:00Z"}]}"#,
            )
            .create();
        let client = RegistryClient::new(server.url());
        let versions = client.get_versions("git-helper").unwrap();
        assert_eq!(versions.len(), 1);
        assert_eq!(versions[0].version, "1.0.0");
    }
}
