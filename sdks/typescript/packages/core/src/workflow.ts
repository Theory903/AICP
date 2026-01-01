export type StepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "skipped"
  | "awaiting_confirmation";

export interface Step {
  id: string;
  capability_name: string;
  arguments?: Record<string, unknown>;
  status?: StepStatus;
  result?: unknown;
  error?: string;
  started_at?: string;
  completed_at?: string;
}

export interface WorkflowState {
  id: string;
  name: string;
  description?: string;
  steps: Step[];
  current_step_index?: number;
  context?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
  status?: "pending" | "running" | "completed" | "failed" | "cancelled";
  created_at?: string;
  updated_at?: string;
}

export interface StepResult {
  success: boolean;
  result?: unknown;
  error?: string;
  requires_confirmation?: boolean;
  next?: {
    action: string;
    workflow_id?: string;
    message?: string;
  };
}
