use crate::nl_workflow::WorkflowSpec;
use serde::{Deserialize, Serialize};

const VALID_STATUSES: &[&str] = &[
    "created",
    "running",
    "waiting_approval",
    "waiting_event",
    "paused",
    "failed",
    "completed",
    "cancelled",
];

const VALID_STEP_TYPES: &[&str] = &[
    "capability",
    "approval",
    "wait_event",
    "branch",
    "parallel",
    "loop",
    "subflow",
    "terminal",
    "human_task",
    "transform",
];

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompileError {
    pub field: String,
    pub message: String,
}

#[derive(Debug, Clone)]
pub struct CompileResult {
    pub valid: bool,
    pub errors: Vec<CompileError>,
}

pub struct WorkflowCompiler {
    _schema_path: String,
}

impl WorkflowCompiler {
    #[must_use]
    pub fn new() -> Self {
        Self {
            _schema_path: "spec/schemas/workflow.schema.json".to_string(),
        }
    }

    #[must_use]
    pub fn with_schema_path(path: impl Into<String>) -> Self {
        Self {
            _schema_path: path.into(),
        }
    }

    #[must_use]
    pub fn compile(&self, spec: &WorkflowSpec) -> CompileResult {
        let mut errors = Vec::new();

        if spec.id.trim().is_empty() {
            errors.push(err("id", "must not be empty"));
        }
        if spec.name.trim().is_empty() {
            errors.push(err("name", "must not be empty"));
        }
        if spec.created_at.trim().is_empty() {
            errors.push(err("created_at", "must not be empty"));
        }
        if spec.updated_at.trim().is_empty() {
            errors.push(err("updated_at", "must not be empty"));
        }
        if spec.steps.is_empty() {
            errors.push(err("steps", "must have at least one step"));
        }

        if !VALID_STATUSES.contains(&spec.status.as_str()) {
            errors.push(err(
                "status",
                &format!("'{}' is not a valid status", spec.status),
            ));
        }

        for (i, step) in spec.steps.iter().enumerate() {
            let path = format!("steps[{i}]");
            if step.id.trim().is_empty() {
                errors.push(err(&format!("{path}.id"), "step id must not be empty"));
            }
            if !VALID_STEP_TYPES.contains(&step.step_type.as_str()) {
                errors.push(err(
                    &format!("{path}.type"),
                    &format!("'{}' is not a valid step type", step.step_type),
                ));
            }
            if step.step_type == "capability" && step.capability_name.is_none() {
                errors.push(err(
                    &format!("{path}.capability_name"),
                    "capability steps must have capability_name",
                ));
            }
            if step.step_type == "subflow"
                && step.subflow_id.as_deref().unwrap_or("").trim().is_empty()
            {
                errors.push(err(
                    &format!("{path}.subflow_id"),
                    "subflow steps must have subflow_id",
                ));
            }
        }

        CompileResult {
            valid: errors.is_empty(),
            errors,
        }
    }
}

impl Default for WorkflowCompiler {
    fn default() -> Self {
        Self::new()
    }
}

fn err(field: &str, message: &str) -> CompileError {
    CompileError {
        field: field.to_string(),
        message: message.to_string(),
    }
}
