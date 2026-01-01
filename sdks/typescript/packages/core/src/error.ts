export interface AicpError {
  code: string;
  message: string;
  fix_hint: string;
  details?: Record<string, unknown>;
  field?: string;
  suggested_value?: unknown;
  related?: string[];
  trace_id?: string;
}
