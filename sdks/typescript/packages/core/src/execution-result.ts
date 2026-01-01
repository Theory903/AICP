export type ExecutionStatus =
  | "success"
  | "failure"
  | "timeout"
  | "rate_limited"
  | "unavailable";

export type NextAction = "continue" | "confirm" | "retry" | "cancel" | "complete" | "wait";

export interface Next {
  action: NextAction;
  capability?: string;
  arguments?: Record<string, unknown>;
  hint?: string;
  message?: string;
  workflow_id?: string;
}

export interface ExecutionResult {
  status: ExecutionStatus;
  data?: unknown;
  error?: string;
  error_code?: string;
  execution_time_ms?: number;
  next: Next;
  rendered?: string;
  format_hint?: "text" | "json" | "table" | "code" | "image";
  can_continue?: boolean;
  continuation_hint?: string;
}
