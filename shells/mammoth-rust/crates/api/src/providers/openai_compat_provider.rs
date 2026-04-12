use std::env;
use std::time::Duration;

use reqwest::Client;
use serde::{Deserialize, Serialize};

use super::{Provider, ProviderFuture};
use crate::error::ApiError;
use crate::types::{
    ContentBlockDelta, ContentBlockDeltaEvent, ContentBlockStartEvent, ContentBlockStopEvent,
    MessageDelta, MessageDeltaEvent, MessageStopEvent, OutputContentBlock, StreamEvent, Usage,
    MessageRequest, MessageResponse,
};

pub const DEFAULT_BASE_URL: &str = "http://127.0.0.1:11434/v1";

fn read_env_var(key: &str) -> Option<String> {
    env::var(key).ok().filter(|v| !v.is_empty())
}

// ── client ────────────────────────────────────────────────────────────────────

#[derive(Clone, Debug)]
pub struct OpenAICompatClient {
    client: Client,
    base_url: String,
    api_key: String,
    model: String,
}

impl OpenAICompatClient {
    pub fn from_env(model: &str) -> Result<Self, ApiError> {
        // Ollama doesn't require an API key; fall back to a dummy value.
        let api_key = read_env_var("OPENAI_API_KEY").unwrap_or_else(|| "ollama".to_string());
        let base_url =
            read_env_var("OPENAI_BASE_URL").unwrap_or_else(|| DEFAULT_BASE_URL.to_string());

        let client = Client::builder()
            .timeout(Duration::from_secs(300))
            .build()
            .map_err(|e| ApiError::Client(format!("Failed to build HTTP client: {e}")))?;

        Ok(Self {
            client,
            base_url,
            api_key,
            model: model.to_string(),
        })
    }
}

// ── wire types ────────────────────────────────────────────────────────────────

#[derive(Serialize)]
struct OAIMessage {
    role: String,
    content: String,
}

#[derive(Serialize)]
struct OAIRequest {
    model: String,
    messages: Vec<OAIMessage>,
    stream: bool,
}

#[derive(Deserialize)]
struct OAIResponse {
    id: String,
    choices: Vec<OAIChoice>,
    model: String,
    usage: OAIUsage,
}

#[derive(Deserialize)]
struct OAIChoice {
    message: OAIMessageContent,
    finish_reason: Option<String>,
}

#[derive(Deserialize)]
struct OAIMessageContent {
    content: String,
}

#[derive(Deserialize)]
struct OAIUsage {
    prompt_tokens: u32,
    completion_tokens: u32,
}

// ── stream (pre-loaded replay) ────────────────────────────────────────────────

/// A pre-loaded stream that replays a complete response as Anthropic-style
/// [`StreamEvent`]s.  We fetch the whole response first (non-streaming) so we
/// don't need a live SSE decoder for OpenAI-format chunks.
#[derive(Debug)]
pub struct OpenAIStream {
    events: Vec<StreamEvent>,
    pos: usize,
}

impl OpenAIStream {
    fn from_response(response: OAIResponse) -> Self {
        let text = response
            .choices
            .first()
            .map(|c| c.message.content.clone())
            .unwrap_or_default();

        let stop_reason = response
            .choices
            .first()
            .and_then(|c| c.finish_reason.clone())
            .unwrap_or_else(|| "end_turn".to_string());

        let usage = Usage {
            input_tokens: response.usage.prompt_tokens,
            cache_creation_input_tokens: 0,
            cache_read_input_tokens: 0,
            output_tokens: response.usage.completion_tokens,
        };

        let events = vec![
            StreamEvent::ContentBlockStart(ContentBlockStartEvent {
                index: 0,
                content_block: OutputContentBlock::Text {
                    text: String::new(),
                },
            }),
            StreamEvent::ContentBlockDelta(ContentBlockDeltaEvent {
                index: 0,
                delta: ContentBlockDelta::TextDelta { text },
            }),
            StreamEvent::ContentBlockStop(ContentBlockStopEvent { index: 0 }),
            StreamEvent::MessageDelta(MessageDeltaEvent {
                delta: MessageDelta {
                    stop_reason: Some(stop_reason),
                    stop_sequence: None,
                },
                usage: usage.clone(),
            }),
            StreamEvent::MessageStop(MessageStopEvent {}),
        ];

        Self { events, pos: 0 }
    }

    pub async fn next_event(&mut self) -> Result<Option<StreamEvent>, ApiError> {
        if self.pos < self.events.len() {
            let event = self.events[self.pos].clone();
            self.pos += 1;
            Ok(Some(event))
        } else {
            Ok(None)
        }
    }
}

// ── provider impl ─────────────────────────────────────────────────────────────

fn extract_messages(request: &MessageRequest) -> Vec<OAIMessage> {
    let mut messages: Vec<OAIMessage> = Vec::new();

    // Inject system prompt if present
    if let Some(ref system) = request.system {
        messages.push(OAIMessage {
            role: "system".to_string(),
            content: system.clone(),
        });
    }

    for m in &request.messages {
        let content = match m.content.first() {
            Some(crate::types::InputContentBlock::Text { text }) => text.clone(),
            Some(crate::types::InputContentBlock::ToolResult { content, .. }) => content
                .first()
                .map(|c| match c {
                    crate::types::ToolResultContentBlock::Text { text } => text.clone(),
                    crate::types::ToolResultContentBlock::Json { value } => value.to_string(),
                })
                .unwrap_or_default(),
            _ => String::new(),
        };
        messages.push(OAIMessage {
            role: m.role.clone(),
            content,
        });
    }

    messages
}

async fn do_fetch(
    client: &Client,
    base_url: &str,
    api_key: &str,
    req: &OAIRequest,
) -> Result<OAIResponse, ApiError> {
    let response = client
        .post(format!("{base_url}/chat/completions"))
        .header("Authorization", format!("Bearer {api_key}"))
        .header("Content-Type", "application/json")
        .json(req)
        .send()
        .await?;

    if !response.status().is_success() {
        let status = response.status();
        let body = response.text().await.unwrap_or_default();
        return Err(ApiError::Api {
            status,
            error_type: None,
            message: None,
            body,
            retryable: false,
        });
    }

    Ok(response.json::<OAIResponse>().await?)
}

impl Provider for OpenAICompatClient {
    type Stream = OpenAIStream;

    fn send_message<'a>(
        &'a self,
        request: &'a MessageRequest,
    ) -> ProviderFuture<'a, MessageResponse> {
        Box::pin(async move {
            let req = OAIRequest {
                model: self.model.clone(),
                messages: extract_messages(request),
                stream: false,
            };

            let chat = do_fetch(&self.client, &self.base_url, &self.api_key, &req).await?;

            let content_text = chat
                .choices
                .first()
                .map(|c| c.message.content.clone())
                .unwrap_or_default();

            Ok(MessageResponse {
                id: chat.id,
                kind: "message".to_string(),
                role: "assistant".to_string(),
                content: vec![crate::types::OutputContentBlock::Text {
                    text: content_text,
                }],
                model: chat.model,
                stop_reason: chat.choices.first().and_then(|c| c.finish_reason.clone()),
                stop_sequence: None,
                usage: Usage {
                    input_tokens: chat.usage.prompt_tokens,
                    cache_creation_input_tokens: 0,
                    cache_read_input_tokens: 0,
                    output_tokens: chat.usage.completion_tokens,
                },
                request_id: None,
            })
        })
    }

    fn stream_message<'a>(
        &'a self,
        request: &'a MessageRequest,
    ) -> ProviderFuture<'a, Self::Stream> {
        Box::pin(async move {
            // Fetch non-streaming, then wrap in a replay stream so the caller
            // can iterate events just like the Anthropic SSE path.
            let req = OAIRequest {
                model: self.model.clone(),
                messages: extract_messages(request),
                stream: false,
            };

            let chat = do_fetch(&self.client, &self.base_url, &self.api_key, &req).await?;
            Ok(OpenAIStream::from_response(chat))
        })
    }
}