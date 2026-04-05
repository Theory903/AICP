use std::collections::{BTreeMap, VecDeque};

use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord)]
pub enum PermissionMode {
    ReadOnly,
    WorkspaceWrite,
    DangerFullAccess,
    Prompt,
    Allow,
}

impl PermissionMode {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::ReadOnly => "read-only",
            Self::WorkspaceWrite => "workspace-write",
            Self::DangerFullAccess => "danger-full-access",
            Self::Prompt => "prompt",
            Self::Allow => "allow",
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PermissionRequest {
    pub tool_name: String,
    pub input: String,
    pub current_mode: PermissionMode,
    pub required_mode: PermissionMode,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PermissionPromptDecision {
    Allow,
    Deny { reason: String },
}

pub trait PermissionPrompter {
    fn decide(&mut self, request: &PermissionRequest) -> PermissionPromptDecision;
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PermissionOutcome {
    Allow,
    Deny { reason: String },
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PermissionPattern {
    pub tool_pattern: String,
    pub input_pattern: Option<String>,
}

impl PermissionPattern {
    #[must_use]
    pub fn new(tool_pattern: impl Into<String>, input_pattern: Option<impl Into<String>>) -> Self {
        Self {
            tool_pattern: tool_pattern.into(),
            input_pattern: input_pattern.map(Into::into),
        }
    }

    #[must_use]
    pub fn matches(&self, tool_name: &str, input: &str) -> bool {
        if !glob_match(&self.tool_pattern, tool_name) {
            return false;
        }
        match &self.input_pattern {
            Some(pat) => glob_match(pat, input),
            None => true,
        }
    }
}

fn glob_match(pattern: &str, value: &str) -> bool {
    if !pattern.contains('*') {
        return pattern == value;
    }
    let parts: Vec<&str> = pattern.splitn(2, '*').collect();
    let (prefix, suffix) = (parts[0], parts[1]);
    if !value.starts_with(prefix) {
        return false;
    }
    let rest = &value[prefix.len()..];
    if suffix.is_empty() {
        return true;
    }
    rest.contains(suffix) || glob_match(suffix, rest)
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PatternRule {
    pub pattern: PermissionPattern,
    pub required_mode: PermissionMode,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PermissionPolicy {
    active_mode: PermissionMode,
    tool_requirements: BTreeMap<String, PermissionMode>,
    pattern_rules: Vec<PatternRule>,
}

impl PermissionPolicy {
    #[must_use]
    pub fn new(active_mode: PermissionMode) -> Self {
        Self {
            active_mode,
            tool_requirements: BTreeMap::new(),
            pattern_rules: Vec::new(),
        }
    }

    #[must_use]
    pub fn with_tool_requirement(
        mut self,
        tool_name: impl Into<String>,
        required_mode: PermissionMode,
    ) -> Self {
        self.tool_requirements
            .insert(tool_name.into(), required_mode);
        self
    }

    #[must_use]
    pub fn with_pattern_rule(
        mut self,
        pattern: PermissionPattern,
        required_mode: PermissionMode,
    ) -> Self {
        self.pattern_rules.push(PatternRule {
            pattern,
            required_mode,
        });
        self
    }

    #[must_use]
    pub fn active_mode(&self) -> PermissionMode {
        self.active_mode
    }

    #[must_use]
    pub fn required_mode_for(&self, tool_name: &str, input: &str) -> PermissionMode {
        for rule in &self.pattern_rules {
            if rule.pattern.matches(tool_name, input) {
                return rule.required_mode;
            }
        }
        self.tool_requirements
            .get(tool_name)
            .copied()
            .unwrap_or(PermissionMode::DangerFullAccess)
    }

    #[must_use]
    pub fn authorize(
        &self,
        tool_name: &str,
        input: &str,
        mut prompter: Option<&mut dyn PermissionPrompter>,
    ) -> PermissionOutcome {
        let current_mode = self.active_mode();
        let required_mode = self.required_mode_for(tool_name, input);
        if current_mode == PermissionMode::Allow || current_mode >= required_mode {
            return PermissionOutcome::Allow;
        }

        let request = PermissionRequest {
            tool_name: tool_name.to_string(),
            input: input.to_string(),
            current_mode,
            required_mode,
        };

        if current_mode == PermissionMode::Prompt
            || (current_mode == PermissionMode::WorkspaceWrite
                && required_mode == PermissionMode::DangerFullAccess)
        {
            return match prompter.as_mut() {
                Some(prompter) => match prompter.decide(&request) {
                    PermissionPromptDecision::Allow => PermissionOutcome::Allow,
                    PermissionPromptDecision::Deny { reason } => PermissionOutcome::Deny { reason },
                },
                None => PermissionOutcome::Deny {
                    reason: format!(
                        "tool '{tool_name}' requires approval to escalate from {} to {}",
                        current_mode.as_str(),
                        required_mode.as_str()
                    ),
                },
            };
        }

        PermissionOutcome::Deny {
            reason: format!(
                "tool '{tool_name}' requires {} permission; current mode is {}",
                required_mode.as_str(),
                current_mode.as_str()
            ),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum OperationalMode {
    #[default]
    Default,
    Plan,
    Bypass,
    Auto,
}

impl OperationalMode {
    #[must_use]
    pub fn as_str(self) -> &'static str {
        match self {
            Self::Default => "default",
            Self::Plan => "plan",
            Self::Bypass => "bypass",
            Self::Auto => "auto",
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct PermissionModeManager;

impl PermissionModeManager {
    #[must_use]
    pub fn effective_mode(&self, op_mode: OperationalMode, trust_tier: u8) -> PermissionMode {
        match op_mode {
            OperationalMode::Default => PermissionMode::WorkspaceWrite,
            OperationalMode::Plan => PermissionMode::ReadOnly,
            OperationalMode::Bypass => PermissionMode::DangerFullAccess,
            OperationalMode::Auto => match trust_tier {
                0..=1 => PermissionMode::ReadOnly,
                2..=3 => PermissionMode::WorkspaceWrite,
                _ => PermissionMode::DangerFullAccess,
            },
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PermissionAuditEntry {
    pub timestamp_ms: u64,
    pub tool_name: String,
    pub input_preview: String,
    pub outcome: String,
    pub mode_at_time: String,
}

#[derive(Debug, Clone)]
pub struct AuditLog {
    entries: VecDeque<PermissionAuditEntry>,
    max_entries: usize,
}

impl AuditLog {
    #[must_use]
    pub fn new(max_entries: usize) -> Self {
        Self {
            entries: VecDeque::new(),
            max_entries,
        }
    }

    pub fn record(&mut self, entry: PermissionAuditEntry) {
        if self.entries.len() >= self.max_entries {
            self.entries.pop_front();
        }
        self.entries.push_back(entry);
    }

    #[must_use]
    pub fn entries(&self) -> &VecDeque<PermissionAuditEntry> {
        &self.entries
    }

    #[must_use]
    pub fn since(&self, since_ms: u64) -> Vec<&PermissionAuditEntry> {
        self.entries
            .iter()
            .filter(|e| e.timestamp_ms >= since_ms)
            .collect()
    }

    #[must_use]
    pub fn last_n(&self, n: usize) -> Vec<&PermissionAuditEntry> {
        self.entries
            .iter()
            .rev()
            .take(n)
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::{
        AuditLog, OperationalMode, PermissionAuditEntry, PermissionMode, PermissionModeManager,
        PermissionOutcome, PermissionPattern, PermissionPolicy, PermissionPromptDecision,
        PermissionPrompter, PermissionRequest,
    };

    struct RecordingPrompter {
        seen: Vec<PermissionRequest>,
        allow: bool,
    }

    impl PermissionPrompter for RecordingPrompter {
        fn decide(&mut self, request: &PermissionRequest) -> PermissionPromptDecision {
            self.seen.push(request.clone());
            if self.allow {
                PermissionPromptDecision::Allow
            } else {
                PermissionPromptDecision::Deny {
                    reason: "not now".to_string(),
                }
            }
        }
    }

    #[test]
    fn allows_tools_when_active_mode_meets_requirement() {
        let policy = PermissionPolicy::new(PermissionMode::WorkspaceWrite)
            .with_tool_requirement("read_file", PermissionMode::ReadOnly)
            .with_tool_requirement("write_file", PermissionMode::WorkspaceWrite);

        assert_eq!(
            policy.authorize("read_file", "{}", None),
            PermissionOutcome::Allow
        );
        assert_eq!(
            policy.authorize("write_file", "{}", None),
            PermissionOutcome::Allow
        );
    }

    #[test]
    fn denies_read_only_escalations_without_prompt() {
        let policy = PermissionPolicy::new(PermissionMode::ReadOnly)
            .with_tool_requirement("write_file", PermissionMode::WorkspaceWrite)
            .with_tool_requirement("bash", PermissionMode::DangerFullAccess);

        assert!(matches!(
            policy.authorize("write_file", "{}", None),
            PermissionOutcome::Deny { reason } if reason.contains("requires workspace-write permission")
        ));
        assert!(matches!(
            policy.authorize("bash", "{}", None),
            PermissionOutcome::Deny { reason } if reason.contains("requires danger-full-access permission")
        ));
    }

    #[test]
    fn prompts_for_workspace_write_to_danger_full_access_escalation() {
        let policy = PermissionPolicy::new(PermissionMode::WorkspaceWrite)
            .with_tool_requirement("bash", PermissionMode::DangerFullAccess);
        let mut prompter = RecordingPrompter {
            seen: Vec::new(),
            allow: true,
        };

        let outcome = policy.authorize("bash", "echo hi", Some(&mut prompter));

        assert_eq!(outcome, PermissionOutcome::Allow);
        assert_eq!(prompter.seen.len(), 1);
        assert_eq!(prompter.seen[0].tool_name, "bash");
        assert_eq!(
            prompter.seen[0].current_mode,
            PermissionMode::WorkspaceWrite
        );
        assert_eq!(
            prompter.seen[0].required_mode,
            PermissionMode::DangerFullAccess
        );
    }

    #[test]
    fn honors_prompt_rejection_reason() {
        let policy = PermissionPolicy::new(PermissionMode::WorkspaceWrite)
            .with_tool_requirement("bash", PermissionMode::DangerFullAccess);
        let mut prompter = RecordingPrompter {
            seen: Vec::new(),
            allow: false,
        };

        assert!(matches!(
            policy.authorize("bash", "echo hi", Some(&mut prompter)),
            PermissionOutcome::Deny { reason } if reason == "not now"
        ));
    }

    #[test]
    fn pattern_matches_wildcard_tool_prefix() {
        let pat = PermissionPattern::new("Bash", Some("git*"));
        assert!(pat.matches("Bash", "git commit -m 'wip'"));
        assert!(!pat.matches("Bash", "rm -rf /"));
        assert!(!pat.matches("FileEdit", "git commit"));
    }

    #[test]
    fn pattern_matches_path_glob() {
        let pat = PermissionPattern::new("FileEdit", Some("/src/*"));
        assert!(pat.matches("FileEdit", "/src/main.rs"));
        assert!(!pat.matches("FileEdit", "/etc/passwd"));
    }

    #[test]
    fn policy_pattern_rules_take_precedence_over_tool_map() {
        let policy2 = PermissionPolicy::new(PermissionMode::WorkspaceWrite)
            .with_pattern_rule(
                PermissionPattern::new("Bash", Some("git*")),
                PermissionMode::WorkspaceWrite,
            )
            .with_tool_requirement("Bash", PermissionMode::DangerFullAccess);
        assert_eq!(
            policy2.authorize("Bash", "git status", None),
            PermissionOutcome::Allow
        );
        assert!(matches!(
            policy2.authorize("Bash", "rm -rf /", None),
            PermissionOutcome::Deny { .. }
        ));
    }

    #[test]
    fn operational_mode_manager_maps_modes_correctly() {
        let mgr = PermissionModeManager;
        assert_eq!(
            mgr.effective_mode(OperationalMode::Plan, 3),
            PermissionMode::ReadOnly
        );
        assert_eq!(
            mgr.effective_mode(OperationalMode::Bypass, 0),
            PermissionMode::DangerFullAccess
        );
        assert_eq!(
            mgr.effective_mode(OperationalMode::Auto, 1),
            PermissionMode::ReadOnly
        );
        assert_eq!(
            mgr.effective_mode(OperationalMode::Auto, 2),
            PermissionMode::WorkspaceWrite
        );
        assert_eq!(
            mgr.effective_mode(OperationalMode::Auto, 4),
            PermissionMode::DangerFullAccess
        );
    }

    #[test]
    fn audit_log_records_and_evicts_oldest_entry() {
        let mut log = AuditLog::new(2);
        log.record(PermissionAuditEntry {
            timestamp_ms: 1000,
            tool_name: "bash".to_string(),
            input_preview: "echo hi".to_string(),
            outcome: "allow".to_string(),
            mode_at_time: "workspace-write".to_string(),
        });
        log.record(PermissionAuditEntry {
            timestamp_ms: 2000,
            tool_name: "read_file".to_string(),
            input_preview: "foo.txt".to_string(),
            outcome: "allow".to_string(),
            mode_at_time: "read-only".to_string(),
        });
        log.record(PermissionAuditEntry {
            timestamp_ms: 3000,
            tool_name: "write_file".to_string(),
            input_preview: "bar.txt".to_string(),
            outcome: "deny".to_string(),
            mode_at_time: "read-only".to_string(),
        });
        assert_eq!(log.entries().len(), 2);
        assert_eq!(log.entries().front().unwrap().timestamp_ms, 2000);
        let since = log.since(2500);
        assert_eq!(since.len(), 1);
        assert_eq!(since[0].tool_name, "write_file");
    }
}
