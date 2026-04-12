use crate::error::ApiError;

use super::mammoth_provider::MammothApiClient;
use super::openai_compat_provider::OpenAICompatClient;
use super::{detect_provider_kind, resolve_model_alias, ProviderKind};

pub enum AnyProvider {
    Anthropic(MammothApiClient),
    OpenAI(OpenAICompatClient),
}

#[derive(Default)]
pub struct ProviderRegistry;

impl ProviderRegistry {
    #[must_use]
    pub fn new() -> Self {
        Self
    }

    pub fn for_model(model: &str) -> Result<AnyProvider, ApiError> {
        let resolved = resolve_model_alias(model);
        let provider_kind = detect_provider_kind(&resolved);

        match provider_kind {
            ProviderKind::Anthropic => Ok(AnyProvider::Anthropic(MammothApiClient::from_env()?)),
            ProviderKind::OpenAI => Ok(AnyProvider::OpenAI(OpenAICompatClient::from_env(
                &resolved,
            )?)),
        }
    }
}
