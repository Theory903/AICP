use crate::nl_workflow::{WorkflowSpec, WorkflowStep};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StepSummary {
    pub step_id: String,
    pub step_type: String,
    pub capability_name: Option<String>,
    pub would_require_approval: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationReport {
    pub steps_would_execute: Vec<StepSummary>,
    pub estimated_duration_ms: u64,
    pub has_approval_gates: bool,
    pub has_parallel_steps: bool,
}

pub struct WorkflowSimulator;

impl WorkflowSimulator {
    #[must_use]
    pub fn new() -> Self {
        Self
    }

    pub fn dry_run(&self, spec: &WorkflowSpec) -> SimulationReport {
        let mut summaries = Vec::new();
        let mut has_approval = false;
        let mut has_parallel = false;

        for step in &spec.steps {
            self.expand_step(step, &mut summaries, &mut has_approval, &mut has_parallel);
        }

        let estimated = summaries.len() as u64 * 50;
        SimulationReport {
            steps_would_execute: summaries,
            estimated_duration_ms: estimated,
            has_approval_gates: has_approval,
            has_parallel_steps: has_parallel,
        }
    }

    fn expand_step(
        &self,
        step: &WorkflowStep,
        out: &mut Vec<StepSummary>,
        has_approval: &mut bool,
        has_parallel: &mut bool,
    ) {
        if step.step_type == "parallel" {
            *has_parallel = true;
            if let Some(sub_steps) = &step.parallel_steps {
                for s in sub_steps {
                    self.expand_step(s, out, has_approval, has_parallel);
                }
            }
        } else {
            if step.step_type == "approval" {
                *has_approval = true;
            }
            out.push(StepSummary {
                step_id: step.id.clone(),
                step_type: step.step_type.clone(),
                capability_name: step.capability_name.clone(),
                would_require_approval: step.step_type == "approval",
            });
        }
    }
}

impl Default for WorkflowSimulator {
    fn default() -> Self {
        Self::new()
    }
}
