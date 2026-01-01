export type CapabilityKind =
  | "query"
  | "action"
  | "workflow"
  | "async_action"
  | "batch_action";

export interface InputSchema {
  type?: string;
  properties?: Record<string, unknown>;
  required?: string[];
  description?: string;
}

export interface OutputSchema {
  type?: string;
  properties?: Record<string, unknown>;
  description?: string;
}

export interface RenderSpec {
  format?: "text" | "json" | "table" | "code" | "image" | "error" | "progress" | "confirmation";
  fields?: string[];
  max_length?: number;
  truncate?: boolean;
  syntax?: string;
  table_columns?: string[];
}

export interface PolicyRef {
  policy_name: string;
  parameters?: Record<string, unknown>;
}

export interface ContinuationSpec {
  can_continue?: boolean;
  next_capabilities?: string[];
  next_hint?: string;
}

export interface ProviderInfo {
  name?: string;
  type?: string;
  url?: string;
}

export interface Capability {
  name: string;
  description?: string;
  kind: CapabilityKind;
  input_schema?: InputSchema;
  output_schema?: OutputSchema;
  tags?: string[];
  policy?: PolicyRef;
  render?: RenderSpec;
  continuation?: ContinuationSpec;
  provider?: ProviderInfo;
  version?: string;
  deprecated?: boolean;
  deprecation_message?: string;
}
