/// Automatic model routing for Mammoth.
///
/// When `--model auto` (or `MAMMOTH_MODEL=auto`) is used, `ModelRouter::select`
/// picks the best model based on task type, context length, and permission mode.
///
/// Routing table (in priority order):
/// 1. `MAMMOTH_MODEL` env var (if not "auto") — explicit override wins
/// 2. Permission mode `danger-full-access` → flagship (most capable) model
/// 3. Task-type hint carried in the prompt or session context:
///    - `code` / `edit` / `refactor` hints → balanced coding model
///    - `quick` / `short` / `explain` hints → fast model
///    - default → flagship model
/// 4. Token budget: if estimated context > 60 000 tokens → model with larger window
///
/// # Usage
/// ```ignore
/// let model = ModelRouter::select(RouterInput {
///     requested: "auto".to_string(),
///     permission_mode: PermissionMode::WorkspaceWrite,
///     prompt_hint: Some("refactor this module"),
///     estimated_tokens: Some(15_000),
/// });
/// ```
use crate::permissions::PermissionMode;

/// Sentinel value: caller asks the router to decide.
pub const AUTO: &str = "auto";

/// Well-known model identifiers used by the router.
pub mod models {
    /// Most capable Claude model — used for complex tasks and elevated permissions.
    pub const FLAGSHIP: &str = "claude-opus-4-6";
    /// Balanced model — good for coding and mid-size contexts.
    pub const BALANCED: &str = "claude-sonnet-4-5";
    /// Fast/cheap model — good for quick Q&A and short explanations.
    pub const FAST: &str = "claude-haiku-3-5";
}

/// Input for `ModelRouter::select`.
#[derive(Clone, Copy)]
pub struct RouterInput<'a> {
    /// The model string the user supplied on the CLI / env.
    /// If it equals `AUTO` the router will choose; otherwise it is passed through.
    pub requested: &'a str,
    /// Active permission mode — `danger-full-access` routes to the flagship.
    pub permission_mode: PermissionMode,
    /// A short hint extracted from the first line of the prompt (lowercased).
    /// The router uses keyword matching on this string.
    pub prompt_hint: Option<&'a str>,
    /// Rough estimate of total tokens in the upcoming request (prompt + history).
    /// Values above `LARGE_CONTEXT_THRESHOLD` will prefer a model with a
    /// larger context window.
    pub estimated_tokens: Option<usize>,
}

/// Estimated token count above which we prefer the flagship (larger window).
const LARGE_CONTEXT_THRESHOLD: usize = 60_000;

/// Keywords in the prompt that suggest a lightweight, fast model is sufficient.
const FAST_KEYWORDS: &[&str] = &[
    "quick",
    "briefly",
    "explain",
    "what is",
    "what are",
    "summarize",
    "tldr",
    "short",
    "one line",
    "one sentence",
];

/// Keywords that suggest a balanced coding-optimised model.
const CODE_KEYWORDS: &[&str] = &[
    "refactor",
    "implement",
    "write a function",
    "write a test",
    "add a",
    "fix the",
    "edit",
    "update the",
    "rename",
    "move the",
];

/// Select the best model for the given input.
///
/// Returns an owned `String` that can be passed directly to `build_runtime`.
#[must_use]
pub fn select(input: RouterInput<'_>) -> String {
    // 1. If the caller supplied an explicit model, honour it verbatim.
    if input.requested != AUTO {
        return input.requested.to_owned();
    }

    // 2. Check MAMMOTH_MODEL env var (allows user-level override without CLI flag).
    if let Ok(env_model) = std::env::var("MAMMOTH_MODEL") {
        let trimmed = env_model.trim().to_owned();
        if !trimmed.is_empty() && trimmed != AUTO {
            return trimmed;
        }
    }

    // 3. Elevated permissions → flagship for maximum capability.
    if matches!(input.permission_mode, PermissionMode::DangerFullAccess) {
        return models::FLAGSHIP.to_owned();
    }

    // 4. Large context → flagship (larger window).
    if input.estimated_tokens.unwrap_or(0) > LARGE_CONTEXT_THRESHOLD {
        return models::FLAGSHIP.to_owned();
    }

    // 5. Keyword matching on the prompt hint.
    if let Some(hint) = input.prompt_hint {
        let lower = hint.to_lowercase();
        if FAST_KEYWORDS.iter().any(|kw| lower.contains(kw)) {
            return models::FAST.to_owned();
        }
        if CODE_KEYWORDS.iter().any(|kw| lower.contains(kw)) {
            return models::BALANCED.to_owned();
        }
    }

    // 6. Default: flagship.
    models::FLAGSHIP.to_owned()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn input<'a>(
        requested: &'a str,
        mode: PermissionMode,
        hint: Option<&'a str>,
        tokens: Option<usize>,
    ) -> RouterInput<'a> {
        RouterInput {
            requested,
            permission_mode: mode,
            prompt_hint: hint,
            estimated_tokens: tokens,
        }
    }

    #[test]
    fn passthrough_non_auto() {
        let model = select(input(
            "claude-opus-4-6",
            PermissionMode::WorkspaceWrite,
            None,
            None,
        ));
        assert_eq!(model, "claude-opus-4-6");
    }

    #[test]
    fn danger_routes_to_flagship() {
        let model = select(input(AUTO, PermissionMode::DangerFullAccess, None, None));
        assert_eq!(model, models::FLAGSHIP);
    }

    #[test]
    fn large_context_routes_to_flagship() {
        let model = select(input(
            AUTO,
            PermissionMode::WorkspaceWrite,
            None,
            Some(80_000),
        ));
        assert_eq!(model, models::FLAGSHIP);
    }

    #[test]
    fn quick_keyword_routes_to_fast() {
        let model = select(input(
            AUTO,
            PermissionMode::WorkspaceWrite,
            Some("briefly explain this"),
            None,
        ));
        assert_eq!(model, models::FAST);
    }

    #[test]
    fn refactor_keyword_routes_to_balanced() {
        let model = select(input(
            AUTO,
            PermissionMode::WorkspaceWrite,
            Some("refactor the auth module"),
            None,
        ));
        assert_eq!(model, models::BALANCED);
    }

    #[test]
    fn default_routes_to_flagship() {
        let model = select(input(AUTO, PermissionMode::WorkspaceWrite, None, None));
        assert_eq!(model, models::FLAGSHIP);
    }
}
