use crate::session::Session;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

const DEFAULT_INPUT_COST_PER_MILLION: f64 = 15.0;
const DEFAULT_OUTPUT_COST_PER_MILLION: f64 = 75.0;
const DEFAULT_CACHE_CREATION_COST_PER_MILLION: f64 = 18.75;
const DEFAULT_CACHE_READ_COST_PER_MILLION: f64 = 1.5;

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct ModelPricing {
    pub input_cost_per_million: f64,
    pub output_cost_per_million: f64,
    pub cache_creation_cost_per_million: f64,
    pub cache_read_cost_per_million: f64,
}

impl ModelPricing {
    #[must_use]
    pub const fn default_sonnet_tier() -> Self {
        Self {
            input_cost_per_million: DEFAULT_INPUT_COST_PER_MILLION,
            output_cost_per_million: DEFAULT_OUTPUT_COST_PER_MILLION,
            cache_creation_cost_per_million: DEFAULT_CACHE_CREATION_COST_PER_MILLION,
            cache_read_cost_per_million: DEFAULT_CACHE_READ_COST_PER_MILLION,
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default, PartialEq, Eq)]
pub struct TokenUsage {
    pub input_tokens: u32,
    pub output_tokens: u32,
    pub cache_creation_input_tokens: u32,
    pub cache_read_input_tokens: u32,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct UsageCostEstimate {
    pub input_cost_usd: f64,
    pub output_cost_usd: f64,
    pub cache_creation_cost_usd: f64,
    pub cache_read_cost_usd: f64,
}

impl UsageCostEstimate {
    #[must_use]
    pub fn total_cost_usd(self) -> f64 {
        self.input_cost_usd
            + self.output_cost_usd
            + self.cache_creation_cost_usd
            + self.cache_read_cost_usd
    }
}

#[must_use]
pub fn pricing_for_model(model: &str) -> Option<ModelPricing> {
    let normalized = model.to_ascii_lowercase();
    if normalized.contains("haiku") {
        return Some(ModelPricing {
            input_cost_per_million: 1.0,
            output_cost_per_million: 5.0,
            cache_creation_cost_per_million: 1.25,
            cache_read_cost_per_million: 0.1,
        });
    }
    if normalized.contains("opus") {
        return Some(ModelPricing {
            input_cost_per_million: 15.0,
            output_cost_per_million: 75.0,
            cache_creation_cost_per_million: 18.75,
            cache_read_cost_per_million: 1.5,
        });
    }
    if normalized.contains("sonnet") {
        return Some(ModelPricing::default_sonnet_tier());
    }
    None
}

impl TokenUsage {
    #[must_use]
    pub fn total_tokens(self) -> u32 {
        self.input_tokens
            + self.output_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
    }

    #[must_use]
    pub fn estimate_cost_usd(self) -> UsageCostEstimate {
        self.estimate_cost_usd_with_pricing(ModelPricing::default_sonnet_tier())
    }

    #[must_use]
    pub fn estimate_cost_usd_with_pricing(self, pricing: ModelPricing) -> UsageCostEstimate {
        UsageCostEstimate {
            input_cost_usd: cost_for_tokens(self.input_tokens, pricing.input_cost_per_million),
            output_cost_usd: cost_for_tokens(self.output_tokens, pricing.output_cost_per_million),
            cache_creation_cost_usd: cost_for_tokens(
                self.cache_creation_input_tokens,
                pricing.cache_creation_cost_per_million,
            ),
            cache_read_cost_usd: cost_for_tokens(
                self.cache_read_input_tokens,
                pricing.cache_read_cost_per_million,
            ),
        }
    }

    #[must_use]
    pub fn summary_lines(self, label: &str) -> Vec<String> {
        self.summary_lines_for_model(label, None)
    }

    #[must_use]
    pub fn summary_lines_for_model(self, label: &str, model: Option<&str>) -> Vec<String> {
        let pricing = model.and_then(pricing_for_model);
        let cost = pricing.map_or_else(
            || self.estimate_cost_usd(),
            |pricing| self.estimate_cost_usd_with_pricing(pricing),
        );
        let model_suffix =
            model.map_or_else(String::new, |model_name| format!(" model={model_name}"));
        let pricing_suffix = if pricing.is_some() {
            ""
        } else if model.is_some() {
            " pricing=estimated-default"
        } else {
            ""
        };
        vec![
            format!(
                "{label}: total_tokens={} input={} output={} cache_write={} cache_read={} estimated_cost={}{}{}",
                self.total_tokens(),
                self.input_tokens,
                self.output_tokens,
                self.cache_creation_input_tokens,
                self.cache_read_input_tokens,
                format_usd(cost.total_cost_usd()),
                model_suffix,
                pricing_suffix,
            ),
            format!(
                "  cost breakdown: input={} output={} cache_write={} cache_read={}",
                format_usd(cost.input_cost_usd),
                format_usd(cost.output_cost_usd),
                format_usd(cost.cache_creation_cost_usd),
                format_usd(cost.cache_read_cost_usd),
            ),
        ]
    }
}

fn cost_for_tokens(tokens: u32, usd_per_million_tokens: f64) -> f64 {
    f64::from(tokens) / 1_000_000.0 * usd_per_million_tokens
}

#[must_use]
pub fn format_usd(amount: f64) -> String {
    format!("${amount:.4}")
}

#[derive(Debug, Clone, Default, PartialEq)]
pub struct UsageTracker {
    latest_turn: TokenUsage,
    cumulative: TokenUsage,
    turns: u32,
    tool_totals: HashMap<String, TokenUsage>,
    peak_turn_tokens: u32,
}

impl UsageTracker {
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    #[must_use]
    pub fn from_session(session: &Session) -> Self {
        let mut tracker = Self::new();
        for message in &session.messages {
            if let Some(usage) = message.usage {
                tracker.record(usage);
            }
        }
        tracker
    }

    pub fn record(&mut self, usage: TokenUsage) {
        self.latest_turn = usage;
        self.cumulative.input_tokens += usage.input_tokens;
        self.cumulative.output_tokens += usage.output_tokens;
        self.cumulative.cache_creation_input_tokens += usage.cache_creation_input_tokens;
        self.cumulative.cache_read_input_tokens += usage.cache_read_input_tokens;
        self.peak_turn_tokens = self.peak_turn_tokens.max(usage.total_tokens());
        self.turns += 1;
    }

    pub fn record_tool(&mut self, tool_name: &str, usage: TokenUsage) {
        let entry = self.tool_totals.entry(tool_name.to_string()).or_default();
        entry.input_tokens += usage.input_tokens;
        entry.output_tokens += usage.output_tokens;
        entry.cache_creation_input_tokens += usage.cache_creation_input_tokens;
        entry.cache_read_input_tokens += usage.cache_read_input_tokens;
    }

    #[must_use]
    pub fn tool_breakdown(&self) -> Vec<ToolUsageRecord> {
        let mut records: Vec<ToolUsageRecord> = self
            .tool_totals
            .iter()
            .map(|(name, usage)| ToolUsageRecord {
                tool_name: name.clone(),
                token_usage: *usage,
            })
            .collect();
        records.sort_by(|a, b| {
            b.token_usage
                .total_tokens()
                .cmp(&a.token_usage.total_tokens())
        });
        records
    }

    #[must_use]
    pub fn check_budget(&self, pricing: ModelPricing, threshold: BudgetThreshold) -> BudgetStatus {
        let cost = self
            .cumulative
            .estimate_cost_usd_with_pricing(pricing)
            .total_cost_usd();
        if cost > threshold.max_cost_usd {
            BudgetStatus::Exceeded {
                overage_usd: cost - threshold.max_cost_usd,
            }
        } else {
            BudgetStatus::Ok
        }
    }

    #[must_use]
    pub fn session_analytics(&self) -> SessionAnalytics {
        let avg = if self.turns == 0 {
            0.0
        } else {
            f64::from(self.cumulative.total_tokens()) / f64::from(self.turns)
        };
        SessionAnalytics {
            avg_tokens_per_turn: avg,
            peak_turn_tokens: self.peak_turn_tokens,
            total_cost_usd: self.cumulative.estimate_cost_usd().total_cost_usd(),
        }
    }

    #[must_use]
    pub fn current_turn_usage(&self) -> TokenUsage {
        self.latest_turn
    }

    #[must_use]
    pub fn cumulative_usage(&self) -> TokenUsage {
        self.cumulative
    }

    #[must_use]
    pub fn turns(&self) -> u32 {
        self.turns
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct ToolUsageRecord {
    pub tool_name: String,
    pub token_usage: TokenUsage,
}

#[derive(Debug, Clone, Copy, PartialEq)]
pub struct BudgetThreshold {
    pub max_cost_usd: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub enum BudgetStatus {
    Ok,
    Exceeded { overage_usd: f64 },
}

#[derive(Debug, Clone, PartialEq)]
pub struct SessionAnalytics {
    pub avg_tokens_per_turn: f64,
    pub peak_turn_tokens: u32,
    pub total_cost_usd: f64,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ModelCostEstimate {
    pub model: String,
    pub cost_usd: f64,
    pub pricing_source: String,
}

pub struct CostEstimator {
    table: HashMap<String, ModelPricing>,
}

impl Default for CostEstimator {
    fn default() -> Self {
        let mut table = HashMap::new();
        table.insert(
            "claude-haiku-4-5".to_string(),
            ModelPricing {
                input_cost_per_million: 1.0,
                output_cost_per_million: 5.0,
                cache_creation_cost_per_million: 1.25,
                cache_read_cost_per_million: 0.1,
            },
        );
        table.insert(
            "claude-sonnet-4-6".to_string(),
            ModelPricing::default_sonnet_tier(),
        );
        table.insert(
            "claude-opus-4-6".to_string(),
            ModelPricing {
                input_cost_per_million: 15.0,
                output_cost_per_million: 75.0,
                cache_creation_cost_per_million: 18.75,
                cache_read_cost_per_million: 1.5,
            },
        );
        table.insert(
            "gpt-4o".to_string(),
            ModelPricing {
                input_cost_per_million: 2.5,
                output_cost_per_million: 10.0,
                cache_creation_cost_per_million: 0.0,
                cache_read_cost_per_million: 1.25,
            },
        );
        table.insert(
            "gemini-1.5-pro".to_string(),
            ModelPricing {
                input_cost_per_million: 1.25,
                output_cost_per_million: 5.0,
                cache_creation_cost_per_million: 0.0,
                cache_read_cost_per_million: 0.31,
            },
        );
        Self { table }
    }
}

impl CostEstimator {
    #[must_use]
    pub fn estimate(&self, model: &str, usage: TokenUsage) -> ModelCostEstimate {
        let default_pricing = ModelPricing::default_sonnet_tier();
        let (pricing, source) = self
            .table
            .get(model)
            .map_or((default_pricing, "default_fallback"), |p| (*p, "known"));
        ModelCostEstimate {
            model: model.to_string(),
            cost_usd: usage
                .estimate_cost_usd_with_pricing(pricing)
                .total_cost_usd(),
            pricing_source: source.to_string(),
        }
    }

    #[must_use]
    pub fn compare_models(&self, usage: TokenUsage, models: &[&str]) -> Vec<ModelCostEstimate> {
        let mut estimates: Vec<ModelCostEstimate> =
            models.iter().map(|m| self.estimate(m, usage)).collect();
        estimates.sort_by(|a, b| {
            a.cost_usd
                .partial_cmp(&b.cost_usd)
                .unwrap_or(std::cmp::Ordering::Equal)
        });
        estimates
    }
}

#[cfg(test)]
mod tests {
    use super::{format_usd, pricing_for_model, TokenUsage, UsageTracker};
    use crate::session::{ContentBlock, ConversationMessage, MessageRole, Session};

    #[test]
    fn tracks_true_cumulative_usage() {
        let mut tracker = UsageTracker::new();
        tracker.record(TokenUsage {
            input_tokens: 10,
            output_tokens: 4,
            cache_creation_input_tokens: 2,
            cache_read_input_tokens: 1,
        });
        tracker.record(TokenUsage {
            input_tokens: 20,
            output_tokens: 6,
            cache_creation_input_tokens: 3,
            cache_read_input_tokens: 2,
        });

        assert_eq!(tracker.turns(), 2);
        assert_eq!(tracker.current_turn_usage().input_tokens, 20);
        assert_eq!(tracker.current_turn_usage().output_tokens, 6);
        assert_eq!(tracker.cumulative_usage().output_tokens, 10);
        assert_eq!(tracker.cumulative_usage().input_tokens, 30);
        assert_eq!(tracker.cumulative_usage().total_tokens(), 48);
    }

    #[test]
    fn computes_cost_summary_lines() {
        let usage = TokenUsage {
            input_tokens: 1_000_000,
            output_tokens: 500_000,
            cache_creation_input_tokens: 100_000,
            cache_read_input_tokens: 200_000,
        };

        let cost = usage.estimate_cost_usd();
        assert_eq!(format_usd(cost.input_cost_usd), "$15.0000");
        assert_eq!(format_usd(cost.output_cost_usd), "$37.5000");
        let lines = usage.summary_lines_for_model("usage", Some("claude-sonnet-4-6"));
        assert!(lines[0].contains("estimated_cost=$54.6750"));
        assert!(lines[0].contains("model=claude-sonnet-4-6"));
        assert!(lines[1].contains("cache_read=$0.3000"));
    }

    #[test]
    fn supports_model_specific_pricing() {
        let usage = TokenUsage {
            input_tokens: 1_000_000,
            output_tokens: 500_000,
            cache_creation_input_tokens: 0,
            cache_read_input_tokens: 0,
        };

        let haiku = pricing_for_model("claude-haiku-4-5-20251213").expect("haiku pricing");
        let opus = pricing_for_model("claude-opus-4-6").expect("opus pricing");
        let haiku_cost = usage.estimate_cost_usd_with_pricing(haiku);
        let opus_cost = usage.estimate_cost_usd_with_pricing(opus);
        assert_eq!(format_usd(haiku_cost.total_cost_usd()), "$3.5000");
        assert_eq!(format_usd(opus_cost.total_cost_usd()), "$52.5000");
    }

    #[test]
    fn marks_unknown_model_pricing_as_fallback() {
        let usage = TokenUsage {
            input_tokens: 100,
            output_tokens: 100,
            cache_creation_input_tokens: 0,
            cache_read_input_tokens: 0,
        };
        let lines = usage.summary_lines_for_model("usage", Some("custom-model"));
        assert!(lines[0].contains("pricing=estimated-default"));
    }

    #[test]
    fn reconstructs_usage_from_session_messages() {
        let session = Session {
            version: 1,
            messages: vec![ConversationMessage {
                role: MessageRole::Assistant,
                blocks: vec![ContentBlock::Text {
                    text: "done".to_string(),
                }],
                usage: Some(TokenUsage {
                    input_tokens: 5,
                    output_tokens: 2,
                    cache_creation_input_tokens: 1,
                    cache_read_input_tokens: 0,
                }),
            }],
        };

        let tracker = UsageTracker::from_session(&session);
        assert_eq!(tracker.turns(), 1);
        assert_eq!(tracker.cumulative_usage().total_tokens(), 8);
    }
}
