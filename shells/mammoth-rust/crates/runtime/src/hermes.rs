use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct HermesMemoryConfig {
    pub enabled: bool,
    pub storage_path: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct HermesSkill {
    pub name: String,
    pub active: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct HermesManager {
    memory_config: HermesMemoryConfig,
    skills: Vec<HermesSkill>,
}

impl HermesManager {
    pub fn new(memory_config: HermesMemoryConfig, skills: Vec<HermesSkill>) -> Self {
        Self {
            memory_config,
            skills,
        }
    }

    pub async fn initialize(&self) -> Result<(), String> {
        Ok(())
    }
}
