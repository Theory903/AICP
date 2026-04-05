#![allow(clippy::many_single_char_names)]
#![allow(clippy::format_push_string)]
#![allow(clippy::must_use_candidate)]
#![allow(clippy::cast_possible_truncation)]
#![allow(clippy::manual_ok_err)]
#![allow(clippy::new_without_default)]
#![allow(clippy::map_unwrap_or)]
#![allow(clippy::uninlined_format_args)]
#![allow(clippy::derivable_impls)]
#![allow(clippy::manual_let_else)]
#![allow(clippy::unused_self)]
#![allow(clippy::return_self_not_must_use)]
#![allow(clippy::collapsible_if)]
#![allow(clippy::unused_async)]
#![allow(clippy::self_only_used_in_recursion)]
#![allow(clippy::write_with_newline)]
#![allow(clippy::wrong_self_convention)]

pub mod adapter;
pub mod adapter_registry;
pub mod session_export;
pub mod session_mux;
pub mod ssh;
pub mod voice;
pub mod channel;
pub mod model_router;
pub mod agent;
pub mod memory;
pub mod skills;
pub mod bash;
pub mod bootstrap;
pub mod compact;
pub mod config;
pub mod conversation;
pub mod file_ops;
pub mod hooks;
pub mod json;
pub mod mcp;
pub mod mcp_client;
pub mod mcp_stdio;
pub mod oauth;
pub mod permissions;
pub mod prompt;
pub mod remote;
pub mod sandbox;
pub mod session;
pub mod usage;
pub mod security;
pub mod tracing;
pub mod telemetry;
pub mod nl_workflow;
pub mod workflow_compiler;
pub mod workflow_simulator;
pub mod flow_builder_tui;

pub use channel::{ApprovalDecision, ApprovalRequest, Channel, ChannelKind};
pub use lsp::{
    FileDiagnostics, LspContextEnrichment, LspError, LspManager, LspServerConfig,
    SymbolLocation, WorkspaceDiagnostics,
};
pub use bash::{execute_bash, BashCommandInput, BashCommandOutput};
pub use bootstrap::{BootstrapPhase, BootstrapPlan};
pub use compact::{
    compact_session, estimate_session_tokens, format_compact_summary,
    get_compact_continuation_message, should_compact, CompactionConfig, CompactionResult,
};
pub use config::{
    AicpConfig, ConfigEntry, ConfigError, ConfigLoader, ConfigSource, McpManagedProxyServerConfig,
    McpConfigCollection, McpOAuthConfig, McpRemoteServerConfig, McpSdkServerConfig,
    McpServerConfig, McpStdioServerConfig, McpTransport, McpWebSocketServerConfig, OAuthConfig,
    ResolvedPermissionMode, RuntimeConfig, RuntimeFeatureConfig, RuntimeHookConfig,
    RuntimePluginConfig, ScopedMcpServerConfig, MAMMOTH_SETTINGS_SCHEMA_NAME,
};
pub use conversation::{
    ApiClient, ApiRequest, AssistantEvent, ConversationRuntime, RuntimeError, StaticToolExecutor,
    ToolError, ToolExecutor, TurnSummary,
};
pub use file_ops::{
    edit_file, glob_search, grep_search, read_file, write_file, EditFileOutput, GlobSearchOutput,
    GrepSearchInput, GrepSearchOutput, ReadFileOutput, StructuredPatchHunk, TextFilePayload,
    WriteFileOutput,
};
pub use hooks::{HookEvent, HookRunResult, HookRunner};
pub use mcp::{
    mcp_server_signature, mcp_tool_name, mcp_tool_prefix, normalize_name_for_mcp,
    scoped_mcp_config_hash, unwrap_ccr_proxy_url,
};
pub use mcp_client::{
    McpManagedProxyTransport, McpClientAuth, McpClientBootstrap, McpClientTransport,
    McpRemoteTransport, McpSdkTransport, McpStdioTransport,
};
pub use mcp_stdio::{
    spawn_mcp_stdio_process, JsonRpcError, JsonRpcId, JsonRpcRequest, JsonRpcResponse,
    ManagedMcpTool, McpInitializeClientInfo, McpInitializeParams, McpInitializeResult,
    McpInitializeServerInfo, McpListResourcesParams, McpListResourcesResult, McpListToolsParams,
    McpListToolsResult, McpReadResourceParams, McpReadResourceResult, McpResource,
    McpResourceContents, McpServerManager, McpServerManagerError, McpStdioProcess, McpTool,
    McpToolCallContent, McpToolCallParams, McpToolCallResult, UnsupportedMcpServer,
};
pub use oauth::{
    clear_oauth_credentials, code_challenge_s256, credentials_path, generate_pkce_pair,
    generate_state, load_oauth_credentials, loopback_redirect_uri, parse_oauth_callback_query,
    parse_oauth_callback_request_target, save_oauth_credentials, OAuthAuthorizationRequest,
    OAuthCallbackParams, OAuthRefreshRequest, OAuthTokenExchangeRequest, OAuthTokenSet,
    PkceChallengeMethod, PkceCodePair,
};
pub use permissions::{
    PermissionMode, PermissionOutcome, PermissionPolicy, PermissionPromptDecision,
    PermissionPrompter, PermissionRequest, AuditLog, PermissionAuditEntry, PermissionModeManager,
    PatternRule, PermissionPattern, OperationalMode,
};
pub use prompt::{
    load_system_prompt, prepend_bullets, ContextFile, ProjectContext, PromptBuildError,
    SystemPromptBuilder, FRONTIER_MODEL_NAME, SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
};
pub use remote::{
    inherited_upstream_proxy_env, no_proxy_list, read_token, upstream_proxy_ws_url,
    RemoteSessionContext, UpstreamProxyBootstrap, UpstreamProxyState, DEFAULT_REMOTE_BASE_URL,
    DEFAULT_SESSION_TOKEN_PATH, DEFAULT_SYSTEM_CA_BUNDLE, NO_PROXY_HOSTS, UPSTREAM_PROXY_ENV_KEYS,
};
pub use session::{ContentBlock, ConversationMessage, MessageRole, Session, SessionError};
pub use session_export::{ExportFormat, SessionExporter};
pub use session_mux::{SessionCommand, SessionMux};
pub use ssh::{SshSessionConfig, SshSessionHandler};
pub use voice::{
    TtsBackend, VoiceCommand, VoiceInput, VoiceInputConfig, VoiceOutput, VoiceOutputConfig,
    WhisperBackend,
};
pub use model_router::{select as route_model, RouterInput, AUTO as MODEL_AUTO};
pub use agent::{
    AgentChannel, AgentConfig, AgentKind, AgentMessage, AgentMessageType, CoordinatorLoop,
    TeamPreset,
};
pub use memory::{EntityRecord, EpisodicEntry, MemoryStore, WorkingMemoryItem};
pub use skills::{load_skill_manifest, SkillError, SkillManifest, SkillRegistry};
pub use usage::{
    format_usd, pricing_for_model, ModelPricing, TokenUsage, UsageCostEstimate, UsageTracker,
    BudgetStatus, BudgetThreshold, CostEstimator, ModelCostEstimate, SessionAnalytics, ToolUsageRecord,
};
pub use security::{SsrfGuard, SsrfCheckResult};
pub use tracing::{PerformanceTracer, SpanHandle, SpanRecord};
pub use nl_workflow::{NlWorkflowParser, WorkflowSpec, WorkflowStep, BranchCondition, ParseError};
pub use workflow_compiler::{WorkflowCompiler, CompileResult, CompileError};
pub use workflow_simulator::{WorkflowSimulator, SimulationReport, StepSummary};
pub use flow_builder_tui::{FlowBuilderOverlay, FlowBuilderAction};

#[cfg(feature = "telemetry")]
pub use telemetry::TelemetryExporter;

#[cfg(test)]
pub(crate) fn test_env_lock() -> std::sync::MutexGuard<'static, ()> {
    static LOCK: std::sync::OnceLock<std::sync::Mutex<()>> = std::sync::OnceLock::new();
    LOCK.get_or_init(|| std::sync::Mutex::new(()))
        .lock()
        .unwrap_or_else(std::sync::PoisonError::into_inner)
}
