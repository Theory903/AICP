use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct OpenHandsConfig {
    pub enable_microagents: bool,
    pub enable_mcp: bool,
}

pub struct OpenHandsManager {
    config: OpenHandsConfig,
}

impl OpenHandsManager {
    pub fn new(config: OpenHandsConfig) -> Self {
        Self { config }
    }

    pub async fn start_agent(&self) -> Result<(), String> {
        Ok(())
    }
}
