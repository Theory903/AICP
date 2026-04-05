export type ShellView = "overview" | "approvals" | "workflows" | "providers";

export interface ApprovalQueueItem {
  id: string;
  status: string;
  capability_name?: string;
  requested_at?: string | null;
}

export interface WorkflowRunItem {
  id: string;
  name?: string;
  status: string;
  current_step_capability?: string | null;
}

export interface ExecutionFeedItem {
  execution_id: string;
  capability_name?: string | null;
  status: string;
  created_at?: string | null;
}

export interface ProviderPulseItem {
  provider_name: string;
  health_status: string;
  failure_rate?: number | null;
  recent_latency_ms?: number | null;
}

export interface ShellSnapshot {
  pendingApprovals: number;
  activeWorkflows: number;
  recentExecutions: number;
  unhealthyProviders: number;
  overallStatus: "healthy" | "attention";
}

export interface ShellDataInput {
  approvals: ApprovalQueueItem[];
  workflows: WorkflowRunItem[];
  executions: ExecutionFeedItem[];
  providers: ProviderPulseItem[];
}

export interface ShellData extends ShellDataInput {
  snapshot: ShellSnapshot;
}

export const SHELL_VIEWS: readonly ShellView[] = [
  "overview",
  "approvals",
  "workflows",
  "providers"
];

const TERMINAL_WORKFLOW_STATES = new Set(["completed", "failed", "cancelled", "rejected"]);

export function deriveShellSnapshot(input: ShellDataInput): ShellSnapshot {
  const pendingApprovals = input.approvals.filter((item) => normalize(item.status) === "pending").length;
  const activeWorkflows = input.workflows.filter(
    (item) => !TERMINAL_WORKFLOW_STATES.has(normalize(item.status))
  ).length;
  const recentExecutions = input.executions.length;
  const unhealthyProviders = input.providers.filter(
    (item) => normalize(item.health_status) !== "healthy"
  ).length;

  return {
    pendingApprovals,
    activeWorkflows,
    recentExecutions,
    unhealthyProviders,
    overallStatus: pendingApprovals > 0 || unhealthyProviders > 0 ? "attention" : "healthy"
  };
}

export function composeShellData(input: ShellDataInput): ShellData {
  return {
    ...input,
    snapshot: deriveShellSnapshot(input)
  };
}

export function normalize(value: string | null | undefined): string {
  return String(value ?? "").trim().toLowerCase();
}
