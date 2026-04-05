use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStep {
    pub id: String,
    #[serde(rename = "type")]
    pub step_type: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub capability_name: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub parallel_steps: Option<Vec<WorkflowStep>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub branch_conditions: Option<Vec<BranchCondition>>,
    pub status: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub subflow_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BranchCondition {
    pub condition: String,
    pub then_step_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowSpec {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub steps: Vec<WorkflowStep>,
    pub status: String,
    pub created_at: String,
    pub updated_at: String,
    pub compensation_policy: String,
}

#[derive(Debug)]
pub struct ParseError(pub String);

pub struct NlWorkflowParser;

impl NlWorkflowParser {
    #[must_use]
    pub fn new() -> Self {
        Self
    }

    pub fn parse(&self, text: &str) -> Result<WorkflowSpec, ParseError> {
        let now = iso_now();
        let id = format!("wf_{}", epoch_ms());
        let steps = self.extract_steps(text)?;
        Ok(WorkflowSpec {
            id,
            name: truncate(text, 60),
            description: Some(text.to_string()),
            steps,
            status: "created".to_string(),
            created_at: now.clone(),
            updated_at: now,
            compensation_policy: "none".to_string(),
        })
    }

    fn extract_steps(&self, text: &str) -> Result<Vec<WorkflowStep>, ParseError> {
        let lower = text.to_lowercase();

        if lower.contains("in parallel") || lower.contains("at the same time") {
            return Ok(vec![Self::build_parallel_step(text)]);
        }

        if lower.contains(" if ") || lower.starts_with("if ") {
            return Ok(vec![Self::build_branch_step(text)]);
        }

        let separators = [
            ", then ",
            ", after that ",
            ", next ",
            ", finally ",
            " then ",
            " after that ",
            " next ",
            " finally ",
            ", ",
        ];
        let mut parts = vec![text.to_string()];
        for sep in separators {
            parts = parts
                .into_iter()
                .flat_map(|p| p.split(sep).map(str::to_string).collect::<Vec<_>>())
                .filter(|p| !p.trim().is_empty())
                .collect();
        }

        if parts.is_empty() {
            return Err(ParseError("no steps parsed from text".to_string()));
        }

        Ok(parts
            .into_iter()
            .enumerate()
            .map(|(i, phrase)| {
                let cap_name = to_snake_case(phrase.trim());
                WorkflowStep {
                    id: format!("step_{i:02}"),
                    step_type: "capability".to_string(),
                    capability_name: Some(cap_name),
                    parallel_steps: None,
                    branch_conditions: None,
                    status: "pending".to_string(),
                    subflow_id: None,
                }
            })
            .collect())
    }

    fn build_parallel_step(text: &str) -> WorkflowStep {
        let base = text.to_lowercase();
        let content = base.split("in parallel").next().unwrap_or(text);
        let sub_phrases: Vec<&str> = content.split(" and ").collect();
        let sub_steps: Vec<WorkflowStep> = sub_phrases
            .iter()
            .enumerate()
            .map(|(i, p)| WorkflowStep {
                id: format!("par_step_{i}"),
                step_type: "capability".to_string(),
                capability_name: Some(to_snake_case(p.trim())),
                parallel_steps: None,
                branch_conditions: None,
                status: "pending".to_string(),
                subflow_id: None,
            })
            .collect();
        WorkflowStep {
            id: "step_parallel_00".to_string(),
            step_type: "parallel".to_string(),
            capability_name: None,
            parallel_steps: Some(sub_steps),
            branch_conditions: None,
            status: "pending".to_string(),
            subflow_id: None,
        }
    }

    fn build_branch_step(text: &str) -> WorkflowStep {
        WorkflowStep {
            id: "step_branch_00".to_string(),
            step_type: "branch".to_string(),
            capability_name: None,
            parallel_steps: None,
            branch_conditions: Some(vec![BranchCondition {
                condition: text.to_string(),
                then_step_id: "step_01".to_string(),
            }]),
            status: "pending".to_string(),
            subflow_id: None,
        }
    }
}

fn to_snake_case(s: &str) -> String {
    s.chars()
        .map(|c| {
            if c.is_alphanumeric() {
                c.to_ascii_lowercase()
            } else {
                '_'
            }
        })
        .collect::<String>()
        .split('_')
        .filter(|p| !p.is_empty())
        .collect::<Vec<_>>()
        .join("_")
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        s.to_string()
    } else {
        format!("{}…", &s[..max])
    }
}

fn epoch_ms() -> u128 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis()
}

fn iso_now() -> String {
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    let (y, mo, d, h, mi, s) = epoch_to_ymd_hms(secs);
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}Z",
        y,
        mo.min(12),
        d.min(31),
        h,
        mi,
        s
    )
}

fn epoch_to_ymd_hms(secs: u64) -> (u64, u64, u64, u64, u64, u64) {
    #[allow(clippy::many_single_char_names)]
    let s = secs % 60;
    let m = (secs / 60) % 60;
    let h = (secs / 3600) % 24;
    let days = secs / 86400;
    let y = 1970 + days / 365;
    let yd = days % 365;
    let mo = yd / 30 + 1;
    let d = yd % 30 + 1;
    (y, mo, d, h, m, s)
}

impl Default for NlWorkflowParser {
    fn default() -> Self {
        Self::new()
    }
}
