use crate::error::ApiError;

use super::mammoth_provider::MammothApiClient;
use super::resolve_model_alias;

pub enum AnyProvider {
    Anthropic(MammothApiClient),
}

#[derive(Default)]
pub struct ProviderRegistry;

impl ProviderRegistry {
    #[must_use]
    pub fn new() -> Self {
        Self
    }

    pub fn for_model(model: &str) -> Result<AnyProvider, ApiError> {
        let _resolved = resolve_model_alias(model);
        Ok(AnyProvider::Anthropic(MammothApiClient::from_env()?))
    }
}
