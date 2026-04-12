export type PolicyEffect = "allow" | "deny" | "ask" | "limit";

export interface PolicySubject {
  capability_name?: string;
  capability_kind?: string;
  provider?: string;
  tags?: string[];
}

export interface PolicyCondition {
  max_rate_per_minute?: number;
  max_amount?: number;
  require_confirmation?: boolean;
  allowed_times?: string;
  ip_whitelist?: string[];
  autonomous_execution?: boolean;
}

export interface Policy {
  name: string;
  description?: string;
  effect: PolicyEffect;
  subject: PolicySubject;
  condition?: PolicyCondition;
  priority?: number;
  metadata?: Record<string, unknown>;
}

export interface PolicyDecision {
  effect: PolicyEffect;
  reason: string;
  policy_name?: string;
  metadata?: Record<string, unknown>;
}

// PolicyResult is returned from policy evaluation (alias for PolicyDecision)
export type PolicyResult = PolicyDecision;
